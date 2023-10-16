import requests
import json


base_url = "https://api.openai.com/v1/chat/completions"
api_key = "YOUR_API_KEY"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
anomaly_str = open('predicted_anomalies.csv').readlines()
anomaly_str = f'\n'.join(anomaly_str)
data = {
    "model": "gpt-3.5-turbo",
    "messages": [
        {"role": "system", "content": "You're a pro at finding anomalies in a basketball game."},
        {"role": "user", "content": f"This data is anomalous, that is, it stands out from other data. Tell me, why can they be anomaly? {anomaly_str}"}
    ]
}

response = requests.post(base_url, headers=headers, data=json.dumps(data))
if response.status_code == 200:
    result = response.json()
    generated_text = result['choices'][0]['message']['content']
    my_file = open('why_anomalies_gpt.txt', 'a+')
    my_file.write(f'\n\n{generated_text}')
    my_file.close()
    print(generated_text)
else:
    print("Ошибка при запросе к API:", response.status_code)
