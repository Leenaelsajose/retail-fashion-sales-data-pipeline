from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime

with DAG(
    'simple_test_dag',
    start_date=datetime(2023, 1, 1),
    schedule_interval=None,
    catchup=False
) as dag:
    echo_task = BashOperator(
        task_id='echo',
        bash_command='echo "Hello from a simple DAG!"',
    )