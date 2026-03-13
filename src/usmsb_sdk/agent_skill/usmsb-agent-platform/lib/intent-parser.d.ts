/**
 * Intent parser for natural language requests.
 */
import { Intent } from "./types";
/**
 * Intent parser class.
 */
export declare class IntentParser {
    /**
     * Parse a natural language request into an Intent.
     */
    parse(request: string): Intent;
    /**
     * Extract parameters from the request based on action type.
     */
    private extractParameters;
    /**
     * Extract skill keywords from request.
     */
    private extractSkills;
}
//# sourceMappingURL=intent-parser.d.ts.map