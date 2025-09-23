A Flask API that runs on one VM in AWS and one VM in GCP.
- Both VMs of the same image provisioned with Terraform
- Both VMs hit with the same load tests
<<<<<<< HEAD
- Results are saved in a JSON file and visualized in a tiny dashboard
- Wrapped in a Python CLI that orchestrates (In Progress)
=======
- Results are saved in a JSON file
- Wrapped in a Python CLI that runs the smoke and load tests for all providers
- Streamlit dashboard to visualize results (In Progress)
>>>>>>> 9812a92 (Created Python CLI, updated Typer logic for formatting results when running all commands)
