#!/usr/bin/env python3
"""
Proto File Code Generator

This script generates Python code from .proto files using grpcio-tools.

Usage:
    python generate_proto.py [--proto-dir DIR] [--output-dir DIR]

Requirements:
    pip install grpcio grpcio-tools
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def generate_proto_files(
    proto_dir: str,
    output_dir: str,
    proto_files: list = None,
) -> bool:
    """
    Generate Python code from proto files.

    Args:
        proto_dir: Directory containing .proto files.
        output_dir: Directory to output generated Python files.
        proto_files: List of specific proto files to generate (optional).

    Returns:
        True if generation was successful.
    """
    try:
        # Check if grpc_tools is installed
        try:
            from grpc_tools import protoc
        except ImportError:
            print("Error: grpcio-tools is not installed.")
            print("Please install it with: pip install grpcio-tools")
            return False

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

        # Find proto files
        if proto_files:
            proto_paths = [os.path.join(proto_dir, f) for f in proto_files]
        else:
            proto_paths = list(Path(proto_dir).glob("*.proto"))

        if not proto_paths:
            print(f"No .proto files found in {proto_dir}")
            return False

        # Generate __init__.py
        init_path = os.path.join(output_dir, "__init__.py")
        if not os.path.exists(init_path):
            with open(init_path, "w") as f:
                f.write('"""Generated gRPC protocol buffer modules."""\n')

        success = True
        for proto_path in proto_paths:
            proto_name = Path(proto_path).stem
            print(f"Generating Python code from {proto_path}...")

            # protoc command arguments
            args = [
                "grpc_tools.protoc",
                f"-I{proto_dir}",  # Proto import path
                f"--python_out={output_dir}",  # Python output
                f"--grpc_python_out={output_dir}",  # gRPC Python output
                str(proto_path),
            ]

            # Run protoc
            result = subprocess.run(
                [sys.executable, "-m", "grpc_tools.protoc"] + args[1:],
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                print(f"Error generating {proto_path}:")
                print(result.stderr)
                success = False
            else:
                print(f"  Generated: {proto_name}_pb2.py")
                print(f"  Generated: {proto_name}_pb2_grpc.py")

                # Add imports to __init__.py
                with open(init_path, "a") as f:
                    f.write(f"\n# {proto_name}\n")
                    f.write(f"from . import {proto_name}_pb2\n")
                    f.write(f"from . import {proto_name}_pb2_grpc\n")

        if success:
            print(f"\nAll proto files generated successfully in {output_dir}")
        else:
            print("\nSome proto files failed to generate.")

        return success

    except Exception as e:
        print(f"Error generating proto files: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate Python code from .proto files"
    )
    parser.add_argument(
        "--proto-dir",
        default=".",
        help="Directory containing .proto files (default: current directory)",
    )
    parser.add_argument(
        "--output-dir",
        default="./generated",
        help="Directory to output generated Python files (default: ./generated)",
    )
    parser.add_argument(
        "--proto-files",
        nargs="*",
        help="Specific proto files to generate (optional, defaults to all)",
    )

    args = parser.parse_args()

    success = generate_proto_files(
        proto_dir=args.proto_dir,
        output_dir=args.output_dir,
        proto_files=args.proto_files,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    # Default generation for this project
    script_dir = Path(__file__).parent
    proto_dir = script_dir
    output_dir = script_dir / "generated"

    print(f"Proto directory: {proto_dir}")
    print(f"Output directory: {output_dir}")

    success = generate_proto_files(
        proto_dir=str(proto_dir),
        output_dir=str(output_dir),
    )

    sys.exit(0 if success else 1)
