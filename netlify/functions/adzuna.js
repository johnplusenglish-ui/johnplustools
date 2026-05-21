export default async (req) => {
  const url = new URL(req.url);
  const what  = url.searchParams.get("what") || "";
  const where = url.searchParams.get("where") || "";

  const params = new URLSearchParams({
    app_id:           "4a47a87c",
    app_key:          "ba5cf21183a50bc025b12b1ae468faf6",
    results_per_page: "10",
    what,
    content_type:     "application/json",
  });
  if (where) params.set("where", where);

  const apiUrl = `https://api.adzuna.com/v1/api/jobs/it/search/1?${params}`;

  try {
    const res  = await fetch(apiUrl);
    const data = await res.json();
    return new Response(JSON.stringify(data), {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (err) {
    return new Response(JSON.stringify({ error: err.message }), {
      status: 500,
      headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
    });
  }
};

export const config = { path: "/api/adzuna" };
