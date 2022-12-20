from pathlib import Path
import random
from abc import ABC, abstractmethod

import hydra
from github import Github
import pandas as pd
import omegaconf


def has_label(issue, label_name: str):
    for label in issue.labels:
        if label.name == label_name:
            return True

    return False


class Revisit(ABC):
    registry = {}

    def __init__(self, session: Github):
        self._session = session

    def __init_subclass__(cls, /, key, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.registry[key] = cls

    # TODO May better to be classmethod
    @abstractmethod
    def summary(self, option: omegaconf.DictConfig) -> str:
        raise NotImplementedError

    @abstractmethod
    def run(self, option: omegaconf.DictConfig):
        raise NotImplementedError


class RevisitRandomIssue(Revisit, key="random_issue"):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def summary(self, option: omegaconf.DictConfig) -> str:
        return f"Random {option.count} issues from repo {option.repo}"

    def run(self, option: omegaconf.DictConfig):
        repo = self._session.get_repo(option.repo)
        issues = list(repo.get_issues(state="all"))

        if "label_to_exclude" in option:
            issues = [issue for issue in issues if not has_label(issue, option.label_to_exclude)]

        picked_issues = random.choices(list(issues), k=option.count)

        records = []
        for issue in picked_issues:
            records.append({
                "url": issue.html_url,
                "title": issue.title,
            })
        df = pd.DataFrame.from_records(records)
        print(self.summary(option))
        print(df.to_markdown(index=False))


class RevisitRandomComment(Revisit, key="random_comment"):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def summary(self, option: omegaconf.DictConfig) -> str:
        return f"Random {option.count} comments from issue {option.repo}#{option.issue_number}"

    def run(self, option: omegaconf.DictConfig):
        repo = self._session.get_repo(option.repo)
        issue = repo.get_issue(option.issue_number)
        comments = list(issue.get_comments())

        picked_comments = random.choices(list(comments), k=option.count)

        records = []
        for comment in picked_comments:
            records.append(
                {
                    "url": comment.html_url,
                    "head": comment.body[:option.head_char_count].replace("\n", " "),
                }
            )
        df = pd.DataFrame.from_records(records)
        print(self.summary(option))
        print(df.to_markdown(index=False))


@hydra.main(version_base="1.2", config_path=".", config_name=Path(__file__).stem)
def main(cfg):
    g = Github(**cfg.session_info)

    for revisit in cfg.revisits:
        Revisit.registry[revisit.type](g).run(revisit.option)


if __name__ == "__main__":
    main()
