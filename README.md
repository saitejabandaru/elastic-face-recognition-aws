# Elastic Face Recognition Web Application (AWS IaaS)

A multi-tier, auto-scaling face recognition system built on AWS using EC2, S3, SQS, and a custom autoscaling controller. The system performs distributed deep learning inference using PyTorch and dynamically scales application-tier instances based on request load.

---

## 🚀 Overview

This project implements an elastic cloud-based face recognition pipeline using AWS Infrastructure-as-a-Service (IaaS).

The system:

- Accepts image upload requests via HTTP
- Stores images in Amazon S3
- Uses Amazon SQS for decoupled communication
- Performs face recognition using a PyTorch model
- Dynamically scales EC2 instances (0–15)
- Scales back to zero when workload completes
- Achieves ~1 second average latency for 100 concurrent requests

---

## 🏗 Architecture
![System Architecture diagram showing three-tier AWS elastic face recognition pipeline with web tier receiving HTTP requests, application tier performing PyTorch inference on EC2 instances, and autoscaling controller managing queue-based scaling from 0 to 15 instances, connected via S3 buckets and SQS queues](assets/architecture.png)
### 1️⃣ Web Tier (`server.py`)
- FastAPI-based HTTP server
- Handles `POST /` requests on port 8000
- Uploads images to S3 input bucket
- Sends filename to SQS request queue
- Waits for prediction from response queue
- Returns result as plain text:

```
<filename>:<prediction>
```

---

### 2️⃣ Application Tier (`backend.py`)
- Runs on EC2 instances (custom AMI)
- Polls SQS request queue
- Downloads image from S3
- Performs PyTorch model inference
- Stores result in S3 output bucket
- Sends prediction to SQS response queue
- Processes one request per instance

---

### 3️⃣ Autoscaling Controller (`controller.py`)
- Custom autoscaling logic (No AWS Auto Scaling service used)
- Monitors SQS request queue depth
- Starts EC2 instances when queue increases
- Stops instances when queue becomes zero
- Supports up to 15 concurrent app-tier instances

---

## ☁️ AWS Services Used

- **EC2** – Web tier + App tier instances
- **S3** – Input and Output storage
- **SQS** – Request and Response queues
- **IAM** – Secure access control
- **Elastic IP** – Static IP for web tier

Region used: `us-east-1`

---

## 📂 Project Structure

```
.
├── web-tier/
│   ├── server.py
│   └── controller.py
│
├── app-tier/
│   └── backend.py
│
├── model/
│   └── data.pt
│
└── README.md
```

---

## ⚙️ Request Flow

1. User uploads image via HTTP POST
2. Image stored in S3 input bucket
3. Filename pushed to SQS request queue
4. App-tier instance processes request
5. Model performs inference
6. Result stored in S3 output bucket
7. Result pushed to SQS response queue
8. Web tier returns prediction to user

---

## 📈 Autoscaling Policy

- 0 instances when no requests
- Scale up based on SQS queue size
- Maximum 15 instances
- Each instance processes exactly 1 request
- Scale back to 0 within seconds after workload ends

---

## 🧠 ML Model

- PyTorch-based face recognition model
- CPU inference
- Deployed via custom EC2 AMI
- Model weights loaded from `data.pt`

---

## 📊 Performance (100 Concurrent Requests)

- ✅ 100% correct predictions
- ✅ 0 failed requests
- ✅ ~0.96s average latency
- ✅ Autoscaled from 0 → 15 → 0 instances
- ✅ All S3 and SQS states validated

---

## 🛠 Technologies Used

- Python
- FastAPI
- PyTorch
- Boto3
- AsyncIO
- AWS EC2, S3, SQS

---

## 🎯 Key Learnings

- Designing elastic distributed systems
- Implementing custom autoscaling logic
- Decoupled communication using SQS
- Cloud-native ML deployment
- Performance tuning for concurrent workloads

---

## Setup Instructions

### Prerequisites

- Python 3.x
- AWS IAM Access Keys
- AWS resources created in `us-east-1`
  - EC2 instances
  - S3 buckets
  - SQS queues

---

### Installation

1. Clone the repository:

```bash
git clone https://github.com/<your-username>/elastic-face-recognition.git
cd elastic-face-recognition
```

2. Install dependencies:

```bash
pip3 install boto3 fastapi uvicorn torch torchvision torchaudio
```

3. Update AWS credentials inside:
- `server.py`
- `backend.py`
- `controller.py`

```python
IAM_ACCESSKEY = "YOUR_ACCESS_KEY"
IAM_SECRETKEY = "YOUR_SECRET_KEY"
```

---

## Running the Application

Start each component separately:

### 1️⃣ Start Backend (App Tier)
```bash
python3 backend.py
```

### 2️⃣ Start Autoscaling Controller
```bash
python3 controller.py
```

### 3️⃣ Start Web Server
```bash
python3 server.py
```

The server will run at:

```
http://<EC2-Elastic-IP>:8000
```

---

## Sending a Test Request

```bash
curl -X POST "http://<Elastic-IP>:8000/" \
  -F "inputFile=@test_000.jpg"
```

Response format:

```
test_000:Prediction
```