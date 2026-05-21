const fetch = require("node-fetch");

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

  try {
    const res  = await fetch(url);
    const data = await res.json();
    return {
      statusCode: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
      body: JSON.stringify(data),
    };
  } catch (err) {
    return {
      statusCode: 500,
      body: JSON.stringify({ error: err.message }),
    };
  }
};
