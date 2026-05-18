(function(global) {
  "use strict";

  function mergeHeaders(base, extra) {
    return Object.assign({}, base || {}, extra || {});
  }

  async function parseResponse(response) {
    const contentType = response.headers.get("content-type") || "";
    if (contentType.indexOf("application/json") >= 0) {
      return response.json();
    }
    return response.text();
  }

  async function request(url, options) {
    const init = Object.assign({ credentials: "same-origin" }, options || {});
    init.headers = mergeHeaders({}, init.headers);

    const response = await fetch(url, init);
    const payload = await parseResponse(response);

    if (!response.ok) {
      const message =
        payload && typeof payload === "object" && payload.detail
          ? String(payload.detail)
          : "Request failed";
      const error = new Error(message);
      error.status = response.status;
      error.payload = payload;
      error.response = response;
      throw error;
    }

    return payload;
  }

  function json(url, options) {
    const init = Object.assign({}, options || {});
    init.headers = mergeHeaders({ "Content-Type": "application/json" }, init.headers);
    return request(url, init);
  }

  function getJSON(url, headers) {
    return json(url, { method: "GET", headers: headers });
  }

  function postJSON(url, body, headers) {
    return json(url, { method: "POST", headers: headers, body: JSON.stringify(body == null ? {} : body) });
  }

  function putJSON(url, body, headers) {
    return json(url, { method: "PUT", headers: headers, body: JSON.stringify(body == null ? {} : body) });
  }

  function patchJSON(url, body, headers) {
    return json(url, { method: "PATCH", headers: headers, body: JSON.stringify(body == null ? {} : body) });
  }

  function deleteJSON(url, headers) {
    return json(url, { method: "DELETE", headers: headers });
  }

  global.SharedAPI = {
    request: request,
    json: json,
    getJSON: getJSON,
    postJSON: postJSON,
    putJSON: putJSON,
    patchJSON: patchJSON,
    deleteJSON: deleteJSON
  };
})(window);
