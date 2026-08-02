from .models import SearchResult


def format_search_result(result: SearchResult) -> str:
    pv = " ".join(f"{r},{c}" for r, c in result.principal_variation) or "-"
    return (
        f"move={result.move} score={result.score} depth={result.completed_depth} "
        f"nodes={result.nodes} time={result.elapsed_ms:.2f}ms "
        f"hits={result.cache_hits} cutoffs={result.cutoffs} pv=[{pv}]"
    )
