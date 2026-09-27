(function () {
  const table = document.getElementById("scansTable");
  const tbody = table.querySelector("tbody");
  const rows = Array.from(tbody.querySelectorAll("tr"));
  const globalSearch = document.getElementById("globalSearch");
  const colFilters = Array.from(document.querySelectorAll(".col-filter"));
  const noResults = document.getElementById("noResults");

  function normalize(s) {
    return (s || "").toString().toLowerCase().trim();
  }

  function applyFilters() {
    const globalTerm = normalize(globalSearch.value);
    const colTerms = colFilters.map((input) => normalize(input.value));

    let visibleCount = 0;

    rows.forEach((row) => {
      const cells = Array.from(row.children).map((td) => normalize(td.textContent));

      const matchesColumns = colTerms.every((term, idx) => {
        if (!term) return true;
        return cells[idx] && cells[idx].includes(term);
      });

      const matchesGlobal = !globalTerm || cells.some((c) => c.includes(globalTerm));

      const visible = matchesColumns && matchesGlobal;
      row.style.display = visible ? "" : "none";
      if (visible) visibleCount += 1;
    });

    noResults.style.display = visibleCount === 0 ? "block" : "none";
  }

  globalSearch.addEventListener("input", applyFilters);
  colFilters.forEach((input) => input.addEventListener("input", applyFilters));
})();
