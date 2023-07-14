#!/usr/bin/env python3
"""Output LaTeX tables and plots.

usage: python3 latex_output.py --input_csv <path_to_input>
                               --output_path <output_path>

This script takes a csv with all the results for each merge and merge tool.
It outputs all three tables in output_path for the latex file. All tables
should be copied into tables/ of the latex project.
"""


import sys
import os
import argparse
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from prettytable import PrettyTable
from merge_tester import MERGE_TOOLS, MERGE_STATES

MERGE_FAILURE_NAMES = [
    MERGE_STATES.Tests_exception.name,
    MERGE_STATES.Tests_timedout.name,
]

MERGE_UNHANDLED_NAMES = [
    MERGE_STATES.Merge_failed.name,
    MERGE_STATES.Merge_timedout.name,
    MERGE_STATES.Merge_exception.name,
]

main_branch_names = ["main", "refs/heads/main", "master", "refs/heads/master"]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_csv", type=str)
    parser.add_argument("--output_path", type=str)
    args = parser.parse_args()
    output_path = args.output_path
    Path(output_path).mkdir(parents=True, exist_ok=True)

    # open results file
    result_df = pd.read_csv(args.input_csv, index_col="idx")

    # figure 1 (stacked area)
    incorrect = []
    correct = []
    unhandled = []
    failure = []
    for merge_tool in MERGE_TOOLS:
        merge_tool_status = result_df[merge_tool]
        correct.append(
            sum(val == MERGE_STATES.Tests_passed.name for val in merge_tool_status)
        )
        incorrect.append(
            sum(val == MERGE_STATES.Tests_failed.name for val in merge_tool_status)
        )
        unhandled.append(sum(val in MERGE_UNHANDLED_NAMES for val in merge_tool_status))
        failure.append(sum(val in MERGE_FAILURE_NAMES for val in merge_tool_status))
        assert incorrect[-1] + correct[-1] + unhandled[-1] + failure[-1] == len(
            merge_tool_status
        )

    fig, ax = plt.subplots()

    ax.bar(MERGE_TOOLS, incorrect, label="Incorrect", color="#1F77B4")
    ax.bar(MERGE_TOOLS, unhandled, bottom=incorrect, label="Unhandled", color="#FF7F0E")
    ax.bar(
        MERGE_TOOLS,
        correct,
        label="Correct",
        bottom=[incorrect[i] + unhandled[i] for i in range(len(MERGE_TOOLS))],
        color="#2CA02C",
    )

    ax.set_ylabel("# of merges")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(reversed(handles), reversed(labels))

    plt.savefig(os.path.join(output_path, "stacked.pdf"))

    # Table 1 (overall results)
    table = """% Do not edit.  This file is automatically generated.
\\begin{tabular}{c|c c|c c|c c}
            Tool & 
            \\multicolumn{2}{|c|}{Correct Merges} & 
            \\multicolumn{2}{|c|}{Unhandled Merges} &
            \\multicolumn{2}{|c}{Incorrect Merges}\\\\
            \\hline
            & \\# & \\% & \\# & \\% & \\# & \\%\\\\ \n"""
    total = len(result_df)
    for merge_tool_idx, merge_tool in enumerate(MERGE_TOOLS):
        correct_percentage = 100 * correct[merge_tool_idx] / total if total != 0 else 0
        unhandled_percentage = (
            100 * unhandled[merge_tool_idx] / total if total != 0 else 0
        )
        incorrect_percentage = (
            100 * incorrect[merge_tool_idx] / total if total != 0 else 0
        )
        table += f"{merge_tool.capitalize()}"
        table += f" & {correct[merge_tool_idx]} & {correct_percentage:.2f}\\%"
        table += f" & {unhandled[merge_tool_idx]} & {unhandled_percentage:.2f}\\%"
        table += f" & {incorrect[merge_tool_idx]} & {incorrect_percentage:.2f}\\%\\\\\n"
    table += "\\end{tabular}\n"

    with open(os.path.join(output_path, "table_summary.txt"), "w") as file:
        file.write(table)

    # Printed Table

    my_table = PrettyTable()
    my_table.field_names = [
        "Merge Tool",
        "Correct Merges",
        "Incorrect Merges",
        "Unhandled Merges",
    ]
    for merge_tool_idx, merge_tool in enumerate(MERGE_TOOLS):
        my_table.add_row(
            [
                merge_tool,
                correct[merge_tool_idx],
                incorrect[merge_tool_idx],
                unhandled[merge_tool_idx],
            ]
        )

    print(my_table)
    if total == 0:
        raise Exception("No merges found in the results file at: " + args.input_csv)

    # Table 2 (by merge source)
    table2 = """% Do not edit.  This file is automatically generated.
\\begin{tabular}{c|c c c c|c c c c|c c c c}
            Tool & 
            \\multicolumn{4}{|c|}{Correct Merges} & 
            \\multicolumn{4}{|c|}{Unhandled Merges} &
            \\multicolumn{4}{|c|}{Incorrect Merges} \\\\
            &
            \\multicolumn{2}{|c}{Main Branch} & 
            \\multicolumn{2}{c|}{Feature Branch} &
            \\multicolumn{2}{|c}{Main Branch} & 
            \\multicolumn{2}{c|}{Feature Branch} &
            \\multicolumn{2}{|c}{Main Branch} & 
            \\multicolumn{2}{c|}{Feature Branch} \\\\
            \\hline
            & \\# & \\% & \\# & \\% & \\# & \\% & \\# & \\% & \\# & \\% & \\# & \\%\\\\ \n"""

    main = result_df[result_df["branch_name"].isin(main_branch_names)]
    feature = result_df[~result_df["branch_name"].isin(main_branch_names)]

    args = []
    for merge_tool_idx, merge_tool in enumerate(MERGE_TOOLS):
        mergem = main[merge_tool]
        mergef = feature[merge_tool]

        correct_main = sum(val == MERGE_STATES.Tests_passed.name for val in mergem)
        correct_main_percentage = (
            100 * correct_main / len(main) if len(main) != 0 else 0
        )
        correct_feature = sum(val == MERGE_STATES.Tests_passed.name for val in mergef)
        correct_feature_percentage = (
            100 * correct_feature / len(feature) if len(feature) > 0 else -1
        )

        incorrect_main = sum(val == MERGE_STATES.Tests_failed.name for val in mergem)
        incorrect_main_percentage = (
            100 * incorrect_main / len(main) if len(main) != 0 else 0
        )
        incorrect_feature = sum(val == MERGE_STATES.Tests_failed.name for val in mergef)
        incorrect_feature_percentage = (
            100 * incorrect_feature / len(feature) if len(feature) > 0 else -1
        )

        unhandled_main = sum(val in MERGE_UNHANDLED_NAMES for val in mergem)
        unhandled_main_percentage = (
            100 * unhandled_main / len(main) if len(main) != 0 else 0
        )
        unhandled_feature = sum(val in MERGE_UNHANDLED_NAMES for val in mergef)
        unhandled_feature_percentage = (
            100 * unhandled_feature / len(feature) if len(feature) > 0 else -1
        )

        table2 += f"            {merge_tool.capitalize()}"
        table2 += f" & {correct_main} & {correct_main_percentage:0.2f}\\%"
        table2 += f" & {correct_feature} & {correct_feature_percentage:0.2f}\\%"
        table2 += f" & {unhandled_main} & {unhandled_main_percentage:0.2f}\\%"
        table2 += f" & {unhandled_feature} & {unhandled_feature_percentage:0.2f}\\%"
        table2 += f" & {incorrect_main} & {incorrect_main_percentage:0.2f}\\%"
        table2 += (
            f" & {incorrect_feature} & {incorrect_feature_percentage:0.2f}\\%\\\\ \n"
        )

    table2 += "\\end{tabular}\n"

    with open(os.path.join(output_path, "table_feature_main_summary.txt"), "w") as file:
        file.write(table2)

    # Table 3 (Runtime)
    table3 = """% Do not edit.  This file is automatically generated.
\\begin{tabular}{c|c|c|c}
    Tool & Mean Runtime & Median Runtime & Max runtime\\\\
    \\hline\n"""

    args = []
    for merge_tool in MERGE_TOOLS:
        table3 += f"    {merge_tool.capitalize()}"
        for f in [np.mean, np.median, np.max]:
            runtime = f(result_df[merge_tool + " runtime"])
            table3 += f" & {runtime:0.2f}"
        table3 += "\\\\\n"
    table3 += "\\end{tabular}\n"

    with open(os.path.join(output_path, "table_runtime.txt"), "w") as file:
        file.write(table3)
