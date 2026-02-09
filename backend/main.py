import os
import json
import asyncio
from fastapi import FastAPI, WebSocket, UploadFile, File, WebSocketDisconnect
from dotenv import load_dotenv

# Modern Google GenAI SDK
from google import genai
from google.genai import types

from s3_service import s3_handler
from rag_service import rag
from engine_service import vehicle_bridge

load_dotenv()
app = FastAPI(title="AutoDialogue Backend")

# Initialize the Modern Client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@app.post("/upload")
async def upload_manual(file: UploadFile = File(...)):
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    # Process into Vector DB and S3
    rag.add_pdf_to_index(temp_path)
    with open(temp_path, "rb") as f:
        s3_url = s3_handler.upload_manual(f, file.filename)
    
    os.remove(temp_path)
    return {"status": "Success", "s3_url": s3_url}

@app.websocket("/ws/diagnose")
async def websocket_diagnose(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive JSON from Kotlin Frontend
            raw_data = await websocket.receive_text()
            user_input = json.loads(raw_data)
            
            print(f"Received data: {user_input}")
            
            # Context Gathering - support both old and new frontend formats
            if 'vehicle' in user_input and 'diagnostics' in user_input:
                # New format from updated frontend
                vehicle = user_input['vehicle']
                diagnostics = user_input['diagnostics']
            else:
                # Fallback to demo data for backward compatibility
                demo_data = vehicle_bridge.get_data()
                vehicle = {'year': 2020, 'make': demo_data.get('make', 'Unknown'), 'model': demo_data.get('model', 'Unknown')}
                diagnostics = {'dtc': demo_data.get('dtc', 'P0000'), 'desc': demo_data.get('desc', 'Unknown'), 'engine_temp': 95, 'rpm': 3000, 'speed': 0, 'engine_load': 0}
            
            text_input = user_input.get('text', '')
            
            # Format diagnostics summary
            diag_summary = f"Engine Temp: {diagnostics.get('engine_temp', 'N/A')}°C, RPM: {diagnostics.get('rpm', 'N/A')}, Speed: {diagnostics.get('speed', 'N/A')}km/h, Engine Load: {diagnostics.get('engine_load', 'N/A')}%"
            
            manual_info = rag.query_manuals(text_input)
            
            prompt = (
                f"You are the persona of a {vehicle['year']} {vehicle['make']} {vehicle['model']}. "
                f"Current issue: {diagnostics['dtc']} - {diagnostics['desc']}. "
                f"Live Data: {diag_summary}. "
                f"Reference Manual Data: {manual_info}. "
                f"User asked: {text_input}"
            )

            # Modern Streaming Call with Search Grounding
            response_stream = client.models.generate_content_stream(
                model='gemini-2.0-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.7
                )
            )

            for chunk in response_stream:
                if chunk.text:
                    await websocket.send_json({
                        "text": chunk.text,
                        "is_final": False,
                        "highlight": "engine" if "misfire" in chunk.text.lower() else None
                    })
            
            # End of response signal
            await websocket.send_json({"text": "", "is_final": True})
            
    except WebSocketDisconnect:
        print("Driver disconnected.")
    except Exception as e:
        print(f"Error: {e}")
        await websocket.close()
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)