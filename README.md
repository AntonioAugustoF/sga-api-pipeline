Data Engineering Project - SGA API Pipeline
This repository contains the implementation of a data pipeline (SGA API Pipeline) designed to extract, transform, and load data efficiently, ensuring data consistency and reliability for downstream analysis and reporting.

The pipeline architecture is built using modular Python scripts and industry-standard practices for clean, scalable data engineering.

Access structured and cleaned data ready for consumption. 💪

Table of Contents
Architecture & Folder Structure

How It Works

Data Extraction

Data Transformation

Data Load

Infrastructure & Orchestration

Prerequisites

Running Project

License

Contact

Architecture & Folder Structure
The project follows a rigorous separation of concerns to ensure maintainability:

Plaintext
sga-api-pipeline/
├── data/               # Local data storage for micro-batches / staging area
├── extract/            # Extraction scripts (APIs, Database connectors)
├── infra/              # Infrastructure configurations and database connections
├── load/               # Loading modules (Data Warehouse / Database insertions)
├── logs/               # Application and pipeline execution logs
├── orchestrators/      # Pipeline automation and scheduling scripts
└── transform/          # Data cleaning, processing, and business logic (Pandas/SQL)
How It Works
Data Extraction
The modules inside the /extract folder are responsible for connecting to source systems (APIs or transactional databases). It fetches new data in batches, ensuring connection security through environment variables (.env).

Data Transformation
Inside the /transform folder, data undergoes rigorous cleaning and structuring:

Data type casting and formatting.

Handling missing values and duplicates.

Applying business rules and preparation for dimensional modeling (Fact and Dimension tables).

Data Load
The processed data from the /load folder is safely written into the target analytical database (Data Warehouse/Data Lake). It uses upsert functionality or append-only strategies depending on the dataset requirements to ensure historical persistence.

Infrastructure & Orchestration
Infrastructure (/infra): Manages database connection pools, environment configuration checks, and logging configurations to track the pipeline health.

Orchestration (/orchestrators): Responsible for triggering the execution flow of the ETL phases (E -> T -> L) in the correct sequence and scheduling periodic runs.

Prerequisites
Software required to run the project locally:

Python 3.10+

Essential packages listed in requirements.txt

Environment file configured (.env)

Running Project
Clone the repository:

Bash
git clone https://github.com/AntonioAugustof/sga-api-pipeline.git
cd sga-api-pipeline
Install dependencies:

Bash
pip install -r requirements.txt
Configure your environment variables:
Create a .env file in the root directory (based on your configuration needs).

Run the pipeline orchestrator:

Bash
python orchestrators/main_pipeline.py
License
Distributed under the MIT License. See LICENSE for more information.

Contact
Please feel free to contact me if you have any questions.

Antonio Augusto - @AntonioAugustoF