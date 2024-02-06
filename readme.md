## General info

This branch contains the code of streamlit app that makes use of basketball statistics to generate tweets. 

Originally it was deployed at https://basnya.streamlit.app

## How to run locally
1. `pip install -r requirements.txt`
2. `mkdir -p .streamlit && cp secrets_temlpate.toml .streamlit/secrets.toml` 
3. Fill `.streamlit/secrets.toml` 
4. `streamlit run sandbox_app.py`
5. Enter password from `.streamlit/secrets.toml` 