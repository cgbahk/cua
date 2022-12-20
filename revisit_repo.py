from pathlib import Path
import random
from abc import ABC, abstractmethod
import re

import hydra
from github import Github
import pandas as pd
import omegaconf


def has_label(issue, label_name: str):
    for label in issue.labels:
        if label.name == label_name:
            return True

    return False


def remove_newline(arg: str):
    return arg.replace("\r", "").replace("\n", " ")


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

        picked_issues = random.choices(issues, k=option.count)

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

        picked_comments = random.choices(comments, k=option.count)

        records = []
        for comment in picked_comments:
            records.append(
                {
                    "url": comment.html_url,
                    "head": remove_newline(comment.body[:option.head_char_count]),
                }
            )
        df = pd.DataFrame.from_records(records)
        print(self.summary(option))
        print(df.to_markdown(index=False))


class RevisitRandomSearch(Revisit, key="random_search"):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def summary(self, option: omegaconf.DictConfig) -> str:
        return f"Random {option.count} items from repo {option.repo} with keyword '{option.keyword}'"

    def run(self, option: omegaconf.DictConfig):
        filtered_issues = list(
            self._session.search_issues(query=f"{option.keyword} repo:{option.repo}")
        )

        picked_issues = random.choices(filtered_issues, k=option.count)

        def keyword_in_title_or_body(*, keyword: str, issue):
            assert issue.title

            if re.search(keyword, issue.title, re.IGNORECASE):
                return True

            if not issue.body:
                return False

            if re.search(keyword, issue.body, re.IGNORECASE):
                return True

            return False

        records = []
        for issue in picked_issues:
            if keyword_in_title_or_body(keyword=option.keyword, issue=issue):
                records.append({
                    "url": issue.html_url,
                    "title_or_head": issue.title,
                })
            else:
                comment_with_keyword = None
                keyword_begin_idx = -1
                for comment in issue.get_comments():
                    result = re.search(option.keyword, comment.body, re.IGNORECASE)
                    if result:
                        comment_with_keyword = comment
                        keyword_begin_idx = result.start()
                        break

                assert comment_with_keyword
                assert keyword_begin_idx >= 0

                head = remove_newline(
                    comment_with_keyword.
                    body[keyword_begin_idx:keyword_begin_idx + option.head_char_count]
                )

                records.append({
                    "url": comment_with_keyword.html_url,
                    "title_or_head": head,
                })

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
