from flask import Flask, render_template, request
from doc_ranker import DocumentRanker
from invertedindexer import InvertedIndexer
import math

app = Flask(__name__)

# -----------------------------
# Step 1: Load the inverted index and create a ranker
# -----------------------------
indexer = InvertedIndexer()
indexer.load_index()
ranker = DocumentRanker(indexer)

# Default number of results per page
DEFAULT_RESULTS_PER_PAGE = 5

# -----------------------------
# Route: Homepage
# -----------------------------
@app.route("/")
def index():
    """
    Render the main search page. Initially no query or results are shown.
    """
    return render_template("index.html", query="", paginated_results=[], no_results=False)

# -----------------------------
# Route: Results (handles search queries)
# -----------------------------
@app.route("/results")
def results():
    """
    Accepts a search query from the user, ranks documents,
    paginates results, and renders them on the same page.
    """
    query = request.args.get("query", "").strip()

    try:
        page = int(request.args.get("page", 1))
    except ValueError:
        page = 1

    try:
        results_per_page = int(request.args.get("per_page", DEFAULT_RESULTS_PER_PAGE))
    except ValueError:
        results_per_page = DEFAULT_RESULTS_PER_PAGE

    # If no query entered, show empty page with prompt
    if not query:
        return render_template(
            "index.html",
            query=query,
            paginated_results=[],
            total_results=0,
            current_page=1,
            total_pages=1,
            page_range=[],
            results_per_page=results_per_page,
            no_results=True
        )

    # -----------------------------
    # Rank documents using your DocumentRanker
    # -----------------------------
    all_results = ranker.rank_documents(query)
    no_results = len(all_results) == 0

    # Preprocess results for template: authors string and score
    for doc in all_results:
        doc['authors_str'] = ", ".join(author['name'] for author in doc.get('authors', []))
        doc['score_display'] = round(doc.get('score', 0), 4)

    # -----------------------------
    # Pagination
    # -----------------------------
    total_results = len(all_results)
    total_pages = max(1, math.ceil(total_results / results_per_page))
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * results_per_page
    end_idx = start_idx + results_per_page
    paginated_results = all_results[start_idx:end_idx]

    # Range of pages to show in pagination links
    start_page = max(1, page - 2)
    end_page = min(total_pages, page + 2)
    page_range = range(start_page, end_page + 1)

    # -----------------------------
    # Render results on index page
    # -----------------------------
    return render_template(
        "index.html",
        query=query,
        paginated_results=paginated_results,
        total_results=total_results,
        current_page=page,
        total_pages=total_pages,
        page_range=page_range,
        results_per_page=results_per_page,
        no_results=no_results
    )


# -----------------------------
# Run the app
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
