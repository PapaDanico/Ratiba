/**
 * API Proxy function — forwards requests to the backend API
 * Handles CORS, authentication headers, and request/response bodies
 */

const BACKEND_URL = process.env.VITE_BACKEND_URL || "http://localhost:8000";

exports.handler = async (event, context) => {
  // Only allow specific HTTP methods
  if (!["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"].includes(event.httpMethod)) {
    return {
      statusCode: 405,
      body: JSON.stringify({ error: "Method not allowed" }),
    };
  }

  // Handle CORS preflight
  if (event.httpMethod === "OPTIONS") {
    return {
      statusCode: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      },
    };
  }

  try {
    // Reconstruct the full path and query string
    const path = event.path.replace("/.netlify/functions/api-proxy", "");
    const queryString = event.rawQuery ? `?${event.rawQuery}` : "";
    const url = `${BACKEND_URL}${path}${queryString}`;

    // Prepare request headers
    const headers = {
      "Content-Type": event.headers["content-type"] || "application/json",
      "X-Forwarded-For": event.headers["client-ip"] || "unknown",
      "X-Forwarded-Proto": "https",
    };

    // Forward Authorization header if present
    if (event.headers.authorization) {
      headers.authorization = event.headers.authorization;
    }

    // Forward cookies if present
    if (event.headers.cookie) {
      headers.cookie = event.headers.cookie;
    }

    // Make the request to the backend
    const response = await fetch(url, {
      method: event.httpMethod,
      headers,
      body: event.body ? event.body : undefined,
    });

    // Read response body
    const contentType = response.headers.get("content-type") || "application/json";
    let responseBody = null;

    if (contentType.includes("application/json") || contentType.includes("text")) {
      responseBody = await response.text();
    } else {
      // For non-text content, return base64
      const buffer = await response.arrayBuffer();
      responseBody = Buffer.from(buffer).toString("base64");
    }

    // Extract Set-Cookie headers (important for session tokens)
    const setCookieHeaders = response.headers.get("set-cookie");
    const responseHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, PATCH, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    };

    if (setCookieHeaders) {
      responseHeaders["set-cookie"] = setCookieHeaders;
    }

    return {
      statusCode: response.status,
      headers: responseHeaders,
      body: responseBody || "",
      isBase64Encoded: !contentType.includes("text") && !contentType.includes("json"),
    };
  } catch (error) {
    console.error("API proxy error:", error);
    return {
      statusCode: 502,
      body: JSON.stringify({
        error: "Bad Gateway",
        message: error instanceof Error ? error.message : "Unknown error",
      }),
    };
  }
};
