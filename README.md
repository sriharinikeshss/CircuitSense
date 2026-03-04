# CircuitSense: AI-Powered Hardware Diagnostic System

CircuitSense is an "Expert System" designed to accelerate hardware engineers during PCB bring-up and failure analysis. Instead of manually cross-referencing thousands of voltage logs against thermal drift, CircuitSense automates the entire ingestion, statistical analysis, and diagnostic pipeline.

It bridges the gap between raw hardware telemetry and human action.

## 🚀 Key Features

*   **Ingestion Engine (BOM Parsing):** Dynamically reconstructs the board's power topology using "Power-First" heuristic text-matching (e.g., LDOs, Buck Converters).
*   **Statistical ML Engine (Isolation Forest):** Mathematically isolates electrical anomalies without requiring thousands of labeled failure examples. We use a **Multivariate Gaussian Tail Population Test** to achieve near 100% false-positive suppression on healthy boards.
*   **Relationship Finder (Spearman Rank Correlation):** Detects non-linear physical relationships (like exponential thermal drift causing voltage drop) by mapping monotonic ranks instead of rigid linear Pearson curves.
*   **AI Diagnostic Engine (Mistral RAG):** Eliminates LLM hallucination by forcing Mistral Large into a rigid "context window." The AI synthesizes the physical BOM, anomaly clusters, and correlation pairs to generate a deterministic engineering test plan.

## 🛠️ Tech Stack

*   **Frontend UI:** Streamlit (Custom "Command Center" Minimalist Styling)
*   **Machine Learning:** Scikit-Learn (Isolation Forest), Pandas, NumPy, SciPy (Spearman Correlation)
*   **LLM Engine:** Mistral Large AI via API
*   **Data Visualization:** Plotly

## ⚙️ Installation & Setup

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/CircuitSense.git
    cd CircuitSense
    ```

2.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Add your API Key:**
    Create a `.env` file in the root directory and add your Mistral API key:
    ```toml
    MISTRAL_API_KEY="your_api_key_here"
    ```

4.  **Run the Application:**
    ```bash
    python -m streamlit run app.py
    ```

## 🧠 Why We Didn't Use Deep Learning

Deep Learning requires thousands of labeled examples of broken boards. In the real world of hardware manufacturing, a 99% yield means broken boards are incredibly rare. 

Isolation Forest is an **unsupervised** algorithm—it doesn't need to know what a "broken" board looks like. It only needs to know what a "normal" board looks like, and it mathematically isolates anything that deviates. Most importantly, it is highly explainable. Engineers can see *why* a board failed, instead of trusting a Deep Learning algorithmic black box.

## 👥 Mission & Authors

CircuitSense was architected to solve the manual bottleneck in hardware bring-up. By fusing deterministic engineering rules with statistical ML and constrained language models, we aim to accelerate modern PCB diagnostics.

**Core Architecture & Engineering Team:**
*   **Sri Hari Nikesh S S**
*   **P Keerthinath**
*   **Mohamed Rayhan S**

## 📄 License

This project is open-sourced under the MIT License - see the [LICENSE](LICENSE) file for details.
