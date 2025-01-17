#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Split the repos list according to the number of machines used.

usage: python3 get_repos.py --repos_csv <path_to_repos.csv>
                            --machine_id <machine_id>
                            --num_machines <num_machines>
                            --output_file <output_path>
This script splits the repos list for each machine and stores the local repos list.
"""

import argparse
from pathlib import Path
import pandas as pd
from loguru import logger

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos_csv", type=Path)
    parser.add_argument("--machine_id", type=int)
    parser.add_argument("--num_machines", type=int)
    parser.add_argument("--output_file", type=Path)
    args = parser.parse_args()
    df: pd.DataFrame = pd.read_csv(args.repos_csv, index_col="idx")
    # Shuffle the dataframe so the ordering of the list doesn't bias the output.
    df = df.sample(frac=1, random_state=42)
    df["split"] = df.index % args.num_machines
    df = df[df["split"] == args.machine_id].drop(columns=["split"])
    df.sort_index(inplace=True)

    df.to_csv(args.output_file, index_label="idx")
    logger.success(
        "Number of local repos in " + str(args.repos_csv) + " = " + str(len(df))
    )
