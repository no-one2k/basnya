## General info
**Title:** BASNya - Basketball Auto-generated Statistical News

**Main idea:** make use of basketball statistics to generate tweets

### Features

- **On-demand Data Retrieval:** The project fetches latest basketball statistics using the nba_api package, ensuring the generated tweets are based on the latest game data.
- **Anomaly Detection:** To find unusual players performances that deserve to write tweet about, the project utilizes extended analytics system and IsolationForest algo.
- **Interpretation:** SHAP is used to extract most unusual stats from detected unusual performances.
- **Tweet Generation:** Utilizing OpenAI API, the project creates creative and informative tweets by combining player statistics.

### Technologies Used

- **Programming Language:** Python
- **API:** [nba_api](https://github.com/swar/nba_api)
- **Data workflows:** [prefect](https://www.prefect.io)
- **ML:** `sklearn` + SHAP
- **Text Generation:** [OpenAI GPT API](https://openai.com/product)
- **Demo UI:** [streamlit](https://streamlit.io) 

**Team:**
- Aleksei
- Bogdan
- Boris

The project was completed as part of the course ["ML System Design. Autumn 23/24"](https://ods.ai/tracks/ml-system-design-23).

## Repo structure

* folder `designdoc` - ML system design documentation 
* branch `discovery` - discovery stage: intermediate results, researches and experiments
* branch `streamlit_app` - final app code 
