#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests the HEAD commits of multiple repos and considers them as valid if the test passes.

usage: python3 test_repo_heads.py --repos_csv_with_hashes <repos_csv_with_hashes.csv>
                                 --output_path <repos_head_passes.csv>
                                 --cache_dir <cache_dir>

Input: a csv of repos.  It must contain a header, one of whose columns is "repository".
That column contains "ORGANIZATION/REPO" for a GitHub repository. The csv must also
contain a column "head hash" which contains a commit hash that will be tested.
Cache_dir is the directory where the cache will be stored.
Output: the rows of the input for which the commit at head hash passes tests.
"""
import multiprocessing
import os
import argparse
from pathlib import Path
import shutil
from functools import partialmethod
from typing import Tuple
from repo import Repository, TEST_STATE
from variables import TIMEOUT_TESTING_PARENT
from tqdm import tqdm
import pandas as pd


if os.getenv("TERM", "dumb") == "dumb":
    tqdm.__init__ = partialmethod(tqdm.__init__, disable=True)  # type: ignore


def num_processes(percentage: float = 0.7) -> int:
    """Compute the number of CPUs to be used
    Args:
        percentage (float, optional): Percentage of CPUs to be used. Defaults to 0.7.
    Returns:
        int: the number of CPUs to be used.
    """
    cpu_count = os.cpu_count() or 1
    processes_used = int(percentage * cpu_count) if cpu_count > 3 else cpu_count
    return processes_used


def head_passes_tests(args: Tuple[pd.Series, Path]) -> pd.Series:
    """Runs tests on the head of the main branch.
    Args:
        args (Tuple[pd.Series,Path]): A tuple containing the repository info and the cache path.
    Returns:
        TEST_STATE: The result of the test.
    """
    repo_info, cache = args
    repo_slug = repo_info["repository"]
    if "/" not in repo_slug:
        repo_info["head test result"] = "Wrong format"
        return repo_info

    if len(repo_info["head hash"]) != 40:
        repo_info["head test result"] = "No valid head hash"
        return repo_info

    print("test_repo_heads:", repo_slug, ": head_passes_tests : started")

    # Load repo
    try:
        repo = Repository(
            repo_slug,
            cache_directory=cache,
            workdir_id=repo_slug + "/head-" + repo_info["repository"],
            lazy_clone=True,
        )
    except Exception as e:
        print("test_repo_heads:", repo_slug, ": exception head_passes_tests :", e)
        repo_info["head test result"] = TEST_STATE.Git_checkout_failed.name
        repo_info["head tree fingerprint"] = None
        return repo_info

    # Test repo
    test_state, _, repo_info["head tree fingerprint"] = repo.checkout_and_test(
        repo_info["head hash"], timeout=TIMEOUT_TESTING_PARENT, n_tests=3
    )
    if test_state == TEST_STATE.Tests_passed:
        # Make sure the repo is cloned and exists
        repo.clone_repo()
        assert (
            repo.repo_path.exists()
        ), f"Repo {repo_slug} does not exist but it has passed tests \
            (Either clone the repo or remove the cache entry)"
    else:
        shutil.rmtree(repo.repo_path, ignore_errors=True)

    repo_info["head test result"] = test_state.name

    print("test_repo_heads:", repo_slug, ": head_passes_tests : returning", test_state)
    return repo_info


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos_csv_with_hashes", type=Path)
    parser.add_argument("--output_path", type=Path)
    parser.add_argument("--cache_dir", type=Path, default="cache/")
    arguments = parser.parse_args()

    Path(arguments.cache_dir).mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(arguments.repos_csv_with_hashes, index_col="idx")

    print("test_repo_heads: Started Testing")
    head_passes_tests_arguments = [(v, arguments.cache_dir) for _, v in df.iterrows()]
    with multiprocessing.Pool(processes=num_processes()) as pool:
        head_passes_tests_results = list(
            tqdm(
                pool.imap(head_passes_tests, head_passes_tests_arguments),
                total=len(head_passes_tests_arguments),
            )
        )
    print("test_repo_heads: Finished Testing")

    print("test_repo_heads: Started Building Output")
    df = pd.DataFrame(head_passes_tests_results)
    filtered_df = df[df["head test result"] == TEST_STATE.Tests_passed.name]
    print("test_repo_heads: Finished Building Output")

    print(
        "test_repo_heads: Number of repos whose head passes tests:",
        len(filtered_df),
        "out of",
        len(df),
    )
    if len(filtered_df) == 0:
        raise Exception("No repos found whose head passes tests")
    filtered_df.to_csv(arguments.output_path, index_label="idx")
    df.to_csv(
        arguments.output_path.parent / "all_repos_head_test_results.csv",
        index_label="idx",
    )
    print("test_repo_heads: Done")
