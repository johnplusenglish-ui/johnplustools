const https = require("https");

exports.handler = async function(event) {
  const what  = event.queryStringParameters?.what  || "";
  const where = event.queryStringParameters?.where || "";

  const params = new URLSearchParams({
    app_id:           "4a47a87c",
    app_key:          "ba5cf21183a50bc025b12b1ae468faf6",
    results_per_page: "10",
    what,
  });
  if (where) params.set("where", where);

  const url = `https://api.adzuna.com/v1/api/jobs/it/search/1?${params}`;

  return new Promise((resolve) => {
    https.get(url, (res) => {
      let data = "";
      res.on("data", chunk => data += chunk);
      res.on("end", () => {
        resolve({
          statusCode: 200,
          headers: {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
          },
          body: data,
        });
      });
    }).on("error", (err) => {
      resolve({
        statusCode: 500,
        body: JSON.stringify({ error: err.message }),
      });
    });
  });
};
