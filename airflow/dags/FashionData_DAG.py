from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable # Although Variable is imported, it's not used in this specific DAG code.
from airflow.exceptions import AirflowException
import papermill as pm
import os
import logging

# Set up logging
logger = logging.getLogger(__name__)

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'max_active_runs': 1,
}

def execute_notebook(**kwargs):
    """
    Execute the Jupyter notebook using Papermill
    """
    # Get the AIRFLOW_HOME directory from the environment variable
    airflow_home = os.environ.get('AIRFLOW_HOME')
    if not airflow_home:
        raise AirflowException("AIRFLOW_HOME environment variable is not set.")

    try:
        # --- MODIFIED PATHS ---
        # Use a path relative to AIRFLOW_HOME for the input notebook
        # Make sure you place your notebook file here in your WSL2 file system
        notebook_path = os.path.join(airflow_home, "notebooks", "Fashion_Data_Pipeline.ipynb")

        # Use a path relative to AIRFLOW_HOME for the output directory
        # This ensures the task has write permissions
        output_dir = os.path.join(airflow_home, "notebook_outputs")
        # --- END MODIFIED PATHS ---

        output_path = os.path.join(output_dir, f"Fashion_Data_Pipeline-output-{kwargs['ds']}.ipynb")

        # Ensure output directory exists
        # The user running the task (your user in WSL2) must have write permissions here
        os.makedirs(output_dir, exist_ok=True)

        # Pass execution context to the notebook
        params = {
            'execution_date': kwargs['execution_date'].isoformat(),
            'dag_run_id': kwargs['dag_run'].run_id,
            'ds': kwargs['ds'],
            'ds_nodash': kwargs['ds_nodash'],
        }

        logger.info(f"Executing notebook: {notebook_path}")
        logger.info(f"Output will be saved to: {output_path}")
        logger.info(f"Parameters passed to notebook: {params}")


        # Execute the notebook with extended timeout (converted to int)
        pm.execute_notebook(
            input_path=notebook_path,
            output_path=output_path,
            parameters=params,
            kernel_name='python3', 
            log_output=True,
            progress_bar=False,
            start_timeout=600,
            execution_timeout=7200, # 2 hours timeout for notebook execution
        )

        logger.info("Notebook execution completed successfully")
        return True

    except FileNotFoundError:
        logger.error(f"Input notebook not found at {notebook_path}")
        raise AirflowException(f"Input notebook not found: {notebook_path}")
    except PermissionError as e:
        logger.error(f"Permission denied: {e}")
        raise AirflowException(f"Permission denied when trying to write to output directory: {e}")
    except Exception as e:
        logger.error(f"Failed to execute notebook: {str(e)}")
        # Re-raise as AirflowException to mark the task as failed
        raise AirflowException(f"Notebook execution failed: {str(e)}")

with DAG(
    'fashion_data_pipeline',
    default_args=default_args,
    description='Daily execution of Fashion Retail Data Pipeline',
    schedule_interval='@daily', 
    catchup=False,
    tags=['data_pipeline', 'fashion', 'papermill'],
) as dag:

    execute_notebook_task = PythonOperator(
        task_id='execute_notebook',
        python_callable=execute_notebook,
        provide_context=True,
        execution_timeout=timedelta(hours=3),
    )

