# Koru API Documentation

## Overview
API endpoints for the Koru story generation platform. The API follows this general flow:

1. Create foundation/session
2. Get available prompts
3. Submit responses
4. Monitor clarity scores
5. Generate story when ready

## Authentication
TBD

## Base URL
All endpoints are relative to: `/api/v1`

## Common Response Formats
All responses follow the format:

json
{
    "status": "success|error",
    "data": { ... },
    "error": {
    "code": "string",
    "message": "string"
}
}

## Error Codes

- `400`: Bad Request - Invalid input
- `401`: Unauthorized - Missing or invalid authentication
- `404`: Not Found - Resource not found
- `500`: Internal Server Error - Unexpected error

## Endpoints
- [Foundation & Session Management](foundation.md)
- [Prompt Management](prompts.md)
- [User Responses](responses.md)
- [Theme Analysis](themes.md)
- [Story Generation](stories.md)

