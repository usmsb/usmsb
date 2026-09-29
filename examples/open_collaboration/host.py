"""LOOPBACK TEST HOST ONLY. Public fixture tokens are NOT production credentials.

Run with the exported/installed usmsb_core package. This process records
agreements; it never executes agent work or fetches artifact URIs.
"""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from usmsb_core.autonomy import CollaborationJournal, ContractError

FIXTURES = {
    "fixture-owner": (
        "owner",
        "test-controller-owner",
        [
            "goal.create",
            "goal.revise",
            "commitment.propose",
            "commitment.accept",
            "adoption.record",
        ],
    ),
    "fixture-provider": (
        "provider",
        "test-controller-provider",
        ["commitment.accept", "artifact.submit"],
    ),
    "fixture-reviewer": ("reviewer", "test-controller-reviewer", ["review.record"]),
}


def serve(path, port=0):
    journal = CollaborationJournal(
        path,
        host_id="local-test-host",
        principals={
            actor: {"controller": controller, "operations": operations}
            for actor, controller, operations in FIXTURES.values()
        },
    )

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, status, result):
            data = json.dumps(result, ensure_ascii=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            self.connection.settimeout(5)
            if self.path != "/commands":
                return self.respond(404, {"error": "not_found"})
            grant = FIXTURES.get(self.headers.get("Authorization", "").removeprefix("Bearer "))
            if not self.headers.get("Authorization", "").startswith("Bearer ") or grant is None:
                return self.respond(401, {"error": "unauthenticated"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 131072:
                    return self.respond(413, {"error": "invalid_body_size"})
                command = json.loads(self.rfile.read(size))
                if not isinstance(command, dict) or set(command) != {
                    "command_id",
                    "operation",
                    "payload",
                }:
                    raise ContractError(
                        "Unexpected envelope fields; identity comes from authentication"
                    )
                result = journal.apply(
                    grant[0], command["command_id"], command["operation"], command["payload"]
                )
                self.respond(200, result)
            except (ContractError, ValueError, TypeError, RecursionError) as exc:
                self.respond(400, {"error": str(exc)[:240]})

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(
        json.dumps({"url": f"http://127.0.0.1:{server.server_port}", "mode": "test_fixtures_only"}),
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    serve(args.db, args.port)
