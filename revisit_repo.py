from pathlib import Path
import random

import hydra
from github import Github
import pandas as pd


@hydra.main(version_base="1.2", config_path=".", config_name=Path(__file__).stem)
def main(cfg):
    g = Github(**cfg.session_info)

    repo = g.get_repo(cfg.repo)
    issues = repo.get_issues(state="all")
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
