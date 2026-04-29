import json
from pathlib import Path

from app.agent.chat_router import ChatRouter


def _safe_div(num: float, den: float) -> float:
    return num / den if den else 0.0


def load_dataset(path: Path) -> list[dict]:
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rows.append(json.loads(line))
    return rows


def calc_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    labels = ["chat", "qa"]
    correct = sum(1 for a, b in zip(y_true, y_pred, strict=False) if a == b)
    accuracy = _safe_div(correct, len(y_true))
    f1_list: list[float] = []
    for label in labels:
        tp = sum(1 for a, b in zip(y_true, y_pred, strict=False) if a == label and b == label)
        fp = sum(1 for a, b in zip(y_true, y_pred, strict=False) if a != label and b == label)
        fn = sum(1 for a, b in zip(y_true, y_pred, strict=False) if a == label and b != label)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        f1_list.append(f1)
    return {"accuracy": accuracy, "macro_f1": sum(f1_list) / len(f1_list)}


def main() -> None:
    base = Path(__file__).resolve().parents[1]
    dataset_path = base / "testdata" / "intent_eval_sample.jsonl"
    rows = load_dataset(dataset_path)
    router = ChatRouter()
    y_true: list[str] = []
    y_pred: list[str] = []
    for row in rows:
        question = str(row["question"])
        label = str(row["label"]).strip().lower()
        pred = router.classify_intent(question)
        y_true.append(label)
        y_pred.append(pred)
    metrics = calc_metrics(y_true, y_pred)
    print(json.dumps({"samples": len(rows), **metrics}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
