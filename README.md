# Pharmacy Prescription Management API

## Overview

This project is a Python Flask backend API designed for managing pharmacy prescriptions. It provides a system for doctors to create and send prescriptions, pharmacists to manage their status and dispense drugs, and for the system to generate standardized prescription labels. The API also offers dashboard features for quick insights into pending tasks and drug prescription statistics.

## Features

*   **User Authentication**: Secure login for registered users (doctors, pharmacists).
*   **Prescription Management**: Create, retrieve, and update the status of prescriptions.
*   **Drug Database**: List available drugs and add new drugs to the system.
*   **Label Generation**: Generate formatted labels for each drug in a prescription.
*   **Pharmacy Dashboard**: View notifications for pending prescriptions and statistics on drug usage.

## Setup and Running the Application

1.  **Create a Virtual Environment (Recommended)**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

2.  **Install Dependencies**:
    Navigate to the project root directory (where `requirements.txt` is located) and run:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**:
    ```bash
    python app.py
    ```
    The Flask development server will start (usually on `http://127.0.0.1:5000/`).
    A `pharmacy.db` SQLite database file will be automatically created in the project root if it doesn't exist.
    On the first run, sample data (test users: 'testdoc'/'doctorpass', 'testpharmacist'/'pharmacistpass', and a few sample drugs) will be populated in the database.

## API Endpoints

Below is a list of available API endpoints:

### Authentication

*   **`POST /login`**
    *   **Purpose**: Authenticates a user and returns user details upon success.
    *   **Request Payload**:
        ```json
        {
          "username": "your_username",
          "password": "your_password"
        }
        ```
    *   **Response Summary**:
        *   `200 OK`: Login successful. Returns `{"message": "Login successful", "user_id": X, "role": "your_role"}`.
        *   `400 Bad Request`: Missing username or password.
        *   `401 Unauthorized`: Invalid credentials.

### Drugs

*   **`GET /drugs`**
    *   **Purpose**: Retrieves a list of all available drugs.
    *   **Request Payload**: None.
    *   **Response Summary**:
        *   `200 OK`: Returns a JSON list of drug objects, e.g., `[{"id": 1, "name": "Amoxicillin", "strength": "250mg", ...}]`.

*   **`POST /drugs`**
    *   **Purpose**: Adds a new drug to the database.
    *   **Request Payload**:
        ```json
        {
          "name": "DrugName",
          "strength": "500mg",
          "instructions": "Take one daily",
          "warnings": "May cause drowsiness"
        }
        ```
    *   **Response Summary**:
        *   `201 Created`: Drug added successfully. Returns `{"message": "Drug added successfully", "drug": {...}}`.
        *   `400 Bad Request`: Missing required fields.

### Prescriptions

*   **`POST /prescriptions`**
    *   **Purpose**: Creates a new prescription. Finds or creates a patient based on `patient_file_number`.
    *   **Request Payload**:
        ```json
        {
          "patient_name": "John Doe",
          "patient_file_number": "PFN12345",
          "doctor_id": 1,
          "drugs": [
            {"drug_id": 1},
            {"drug_id": 2}
          ]
        }
        ```
    *   **Response Summary**:
        *   `201 Created`: Prescription created. Returns `{"message": "Prescription created successfully", "prescription_id": X, ...}`.
        *   `400 Bad Request`: Missing fields, invalid drug ID, or empty drugs list.
        *   `403 Forbidden`: Invalid or unauthorized `doctor_id`.

*   **`GET /prescriptions/{prescription_id}`**
    *   **Purpose**: Retrieves details of a specific prescription.
    *   **Request Payload**: None.
    *   **Response Summary**:
        *   `200 OK`: Returns prescription details including patient, doctor, and drug information.
        *   `404 Not Found`: Prescription with the given ID not found.

*   **`PUT /prescriptions/{prescription_id}/status`**
    *   **Purpose**: Updates the status of a specific prescription.
    *   **Request Payload**:
        ```json
        {
          "status": "ready"
        }
        ```
    *   **Response Summary**:
        *   `200 OK`: Status updated. Returns `{"message": "Prescription status updated successfully", "prescription": {...}}`.
        *   `400 Bad Request`: Missing `status` field.
        *   `404 Not Found`: Prescription not found.

### Labels

*   **`GET /prescriptions/{prescription_id}/label`**
    *   **Purpose**: Generates formatted labels for each drug in a given prescription.
    *   **Request Payload**: None.
    *   **Response Summary**:
        *   `200 OK`: Returns a JSON object with `prescription_id` and a list of `labels` (formatted strings). Example:
            ```json
            {
              "prescription_id": 1,
              "labels": [
                "name of patient: John Doe\nfile number: P12345\ndrug name: Amoxicillin...",
                "name of patient: John Doe\nfile number: P12345\ndrug name: Ibuprofen..."
              ]
            }
            ```
        *   `404 Not Found`: Prescription not found.

### Dashboard

*   **`GET /dashboard/notifications`**
    *   **Purpose**: Retrieves a list of all prescriptions currently in 'pending' status.
    *   **Request Payload**: None.
    *   **Response Summary**:
        *   `200 OK`: Returns a JSON list of pending prescriptions, e.g., `[{"id": 1, "patient_name": "Jane Doe", "created_at": "..."}]`. An empty list if none are pending.

*   **`GET /dashboard/statistics/drug_prescriptions`**
    *   **Purpose**: Provides statistics on how many times each drug has been prescribed.
    *   **Request Payload**: None.
    *   **Response Summary**:
        *   `200 OK`: Returns a JSON object where keys are drug names and values are their prescription counts, e.g., `{"Amoxicillin": 10, "Panadol": 25}`.

## Running Tests

To run the automated unit tests for the API, navigate to the project root and execute:

```bash
python test_app.py
```

This will run all tests defined in `test_app.py` using an in-memory SQLite database.
