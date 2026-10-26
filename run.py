"""Run everything: python run.py  (add --no-download to reuse the saved Kaggle files)."""
import sys

from qcom import data, experiment, findings

if __name__ == "__main__":
    if "--no-download" not in sys.argv:
        data.download()
    data.load()
    data.dbt("deps")
    data.dbt("build", "--exclude", "path:models/staging/experiment", "experiment_users")
    experiment.simulate()
    data.dbt("build", "--select", "+experiment_users")
    experiment.analyse()
    findings.run()
