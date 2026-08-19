let
    SourceType = DataSourceType,

    // Source 1: PostgreSQL Direct Database Connection via PgBouncer
    DBSource = PostgreSQL.Database("localhost:6432", "edu_metrics", [Query="SELECT * FROM yearly_metrics"]),

    // Source 2: Combined CSV Folder Directory
    CSVSource = Folder.Files("C:\Data\HigherEduCSVs"),
    CombinedCSV = Table.Combine(List.Transform(CSVSource[Content], Csv.Document)),

    // Source 3: Embedded Python Threading Loader
    PythonSource = Python.Execute(
        "import pandas as pd#(lf)" &
        "import concurrent.futures#(lf)" &
        "def fetch(u): return pd.DataFrame([{'uni_id': u, 'academic_year': 2024, 'attendees': 5000, 'graduates': 1200}])#(lf)" &
        "with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:#(lf)" &
        "    res = list(ex.map(fetch, [101,102,103,104,105]))#(lf)" &
        "final_dataset = pd.concat(res, ignore_index=True)"
    ){[Name="final_dataset"]}[Data],

    // Dynamic Switch Evaluation
    FinalDataset = if SourceType = "DB" then DBSource
                   else if SourceType = "CSV" then CombinedCSV
                   else PythonSource
in
    FinalDataset
