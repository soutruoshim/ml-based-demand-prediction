# Machine Learning Demand Prediction

Complete final project for predicting monthly demand for Shampoo, Body Wash, and Laundry Detergent. The included dataset is **synthetic demonstration data**, not real Medtherm factory data.

## Run

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/train_model.py
.venv/bin/python src/sync_final_report.py
.venv/bin/python src/create_presentation.py
```

The training workflow deterministically regenerates the dataset, trains three regression models with a time-aware holdout, and writes all tables and figures to `outputs/`. The presentation script creates the final-defense deck at `presentation/ML_Demand_Prediction_Final_Defense.pptx`.

## Web application

Run the API and React UI in two terminals:

```bash
.venv/bin/uvicorn api.main:app --reload --port 8000
cd web && npm install && npm run dev
```

Open `http://localhost:5173`, import a CSV, and select **Analyze dataset**. API documentation is available at `http://localhost:8000/docs`.

## Project contents

- `src/train_model.py`: data generation, preprocessing, training, evaluation, interpretation, and planning output
- `src/create_presentation.py`: reproducible 12-slide final-defense presentation
- `src/sync_final_report.py`: synchronizes the paper's metrics, tables, sample rows, and figures with verified outputs
- `data/synthetic_factory_demand_dataset.csv`: 177 synthetic monthly product records
- `outputs/`: evaluation tables, predictions, feature importance, planning output, charts, and serialized best model
- `Final_Deliverables_ML_Demand_Prediction.docx`: journal-style final paper
- `ML-Prediction Factory Production Plannings.pdf`: approved midterm proposal
- `ML_Midterm_Final_Assignment_Guideline.pdf`: course rubric

## Replace with real data

Use the same columns as the generated CSV and run:

```bash
.venv/bin/python src/train_model.py --data path/to/authorized_factory_data.csv
```

Required columns are documented by `--help`. Results from synthetic data must not be represented as real factory evidence.
