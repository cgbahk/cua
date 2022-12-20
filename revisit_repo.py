from pathlib import Path
import random

import hydra
from github import Github
import pandas as pd


def has_label(issue, label_name: str):
    for label in issue.labels:
        if label.name == label_name:
            return True

    return False


@hydra.main(version_base="1.2", config_path=".", config_name=Path(__file__).stem)
def main(cfg):
    g = Github(**cfg.session_info)

    repo = g.get_repo(cfg.repo)
    issues = list(repo.get_issues(state="all"))

    if "label_to_exclude" in cfg:
        issues = [issue for issue in issues if not has_label(issue, cfg.label_to_exclude)]

    picked_issues = random.choices(list(issues), k=cfg.issue_pick_count)

    records = []
    for issue in picked_issues:
        records.append({
            "url": issue.html_url,
            "title": issue.title,
        })
    df = pd.DataFrame.from_records(records)
    print(df.to_markdown(index=False))


if __name__ == "__main__":
    main()
