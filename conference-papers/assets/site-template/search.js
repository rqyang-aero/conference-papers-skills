(function () {
  const input = document.getElementById("site-search");
  const results = document.getElementById("search-results");
  if (!input || !results) return;

  const indexPath = window.SEARCH_INDEX_PATH || "search-index.json";
  const rootPrefix = indexPath.replace(/search-index\.json$/, "");
  let papers = [];

  function render(items) {
    if (!input.value.trim()) {
      results.innerHTML = "<p>Type to search titles, authors, topics, and abstracts.</p>";
      return;
    }
    results.innerHTML = items.slice(0, 12).map((paper) => {
      const meta = [paper.conference, paper.year, (paper.topics || []).join(", ")].filter(Boolean).join(" · ");
      return `<div class="result"><strong><a href="${rootPrefix}${paper.url}">${paper.title}</a></strong><br><span>${meta}</span></div>`;
    }).join("") || "<p>No matches.</p>";
  }

  function searchable(paper) {
    return [
      paper.title,
      (paper.authors || []).join(" "),
      paper.conference,
      paper.year,
      (paper.topics || []).join(" "),
      paper.abstract,
    ].join(" ").toLowerCase();
  }

  fetch(indexPath)
    .then((response) => response.json())
    .then((data) => {
      papers = data.map((paper) => Object.assign({}, paper, { haystack: searchable(paper) }));
      render([]);
    })
    .catch(() => {
      results.innerHTML = "<p>Search index unavailable.</p>";
    });

  input.addEventListener("input", () => {
    const terms = input.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    render(papers.filter((paper) => terms.every((term) => paper.haystack.includes(term))));
  });
})();
