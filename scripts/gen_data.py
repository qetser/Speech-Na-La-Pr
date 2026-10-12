"""Generate a large synthetic Gram Panchayat benchmark + training corpus.

Writes:
  data/benchmark_large/reports.csv       (500 rows + header)
  data/corpus/marathi_admin_large.txt    (deterministic Marathi reports, 500x)
"""
import csv
import io
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.generate import generate_deterministic
from pipeline.ground import ground
from pipeline.parse import parse_csv
from pipeline.run import DEFAULT_SCHEMA
from pipeline.schema import load_schema

random.seed(42)
schema = load_schema(DEFAULT_SCHEMA)

HEADER = ["gp_name", "taluka", "district", "period", "households",
          "works_done", "funds_received", "funds_spent", "beneficiaries"]

VILLAGES = ["शिरूर", "वडगाव", "आंबेगाव", "पिंपळगाव", "सोनगाव", "रामपूर", "कृष्णानगर",
            "गणेशवाडी", "शिवाजीनगर", "नवीनगर", "देऊळगाव", "धामणगाव", "वाघोली", "लोणी",
            "तळेगाव", "चाकण", "राजगुरुनगर", "मंचर", "नारायणगाव", "ओतूर", "आळंदी",
            "केडगाव", "यवत", "पाटस", "निरा", "वालचंदनगर", "भिगवण", "टाकळी", "सासवड", "जेजुरी"]
TALUKAS = ["शिरूर", "हवेली", "मालेगाव", "कर्जत", "पैठण", "तासगाव", "वाई", "उदगीर",
           "आंबेगाव", "दौंड", "इंदापूर", "बारामती", "मावळ", "जुन्नर", "खेड", "मुळशी",
           "पुरंदर", "भोर", "कराड", "पाटण", "माण", "खटाव", "फलटण", "कोरेगाव"]
DISTRICTS = ["पुणे", "नाशिक", "नागपूर", "छत्रपती संभाजीनगर", "कोल्हापूर", "सातारा",
             "सांगली", "सोलापूर", "अहमदनगर", "रायगड", "ठाणे", "जळगाव", "लातूर", "बीड",
             "नांदेड", "अमरावती", "यवतमाळ", "वर्धा", "चंद्रपूर", "भंडारा", "धुळे",
             "रत्नागिरी", "परभणी", "बुलढाणा", "पालघर", "जालना"]
PERIODS = ["एप्रिल-जून २०२५", "जुलै-सप्टेंबर २०२५", "ऑक्टोबर-डिसेंबर २०२५",
           "जानेवारी-मार्च २०२६", "एप्रिल-जून २०२६", "जुलै-सप्टेंबर २०२६"]


def make_row() -> list:
    recv = random.randrange(500_000, 5_000_000, 10_000)
    spent = int(round(recv * random.uniform(0.70, 0.98) / 1000) * 1000)
    return [
        random.choice(VILLAGES) + " ग्रामपंचायत",
        random.choice(TALUKAS), random.choice(DISTRICTS), random.choice(PERIODS),
        random.randint(300, 3000), random.randint(5, 50), recv, spent,
        random.randint(100, 2000),
    ]


def main() -> None:
    rows = [make_row() for _ in range(500)]

    bench = ROOT / "data" / "benchmark_large"
    bench.mkdir(parents=True, exist_ok=True)
    with (bench / "reports.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        w.writerows(rows)

    corpus_lines = []
    header_line = ",".join(HEADER)
    for row in rows:
        csv_text = header_line + "\n" + ",".join(str(x) for x in row)
        record = parse_csv(csv_text)
        slots = generate_deterministic(ground(record, schema), schema)
        for s in slots:
            corpus_lines.append("".join(t["text"] for t in s["tokens"]))
        corpus_lines.append("")
    corpus = ROOT / "data" / "corpus" / "marathi_admin_large.txt"
    corpus.write_text("\n".join(corpus_lines), encoding="utf-8")

    print(f"reports.csv: {len(rows)} rows (+header) = {len(rows)+1} lines")
    print(f"corpus: {len(corpus_lines)} lines")


if __name__ == "__main__":
    main()
