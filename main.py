from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi

app = FastAPI()

class TranscriptRequest(BaseModel):
    video_id: str

@app.post("/transcript")
async def get_transcript(data: TranscriptRequest):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(data.video_id, languages=['en'])

        # ✅ This is a list of dicts. Let's build a plain text string.
        lines = []
        for segment in transcript:
            text = segment.get("text", "")
            lines.append(text)
        
        full_text = " ".join(lines)  # Join all segments together
        return {"transcript": full_text}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))





# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# from youtube_transcript_api import YouTubeTranscriptApi
# from youtube_transcript_api.formatters import TextFormatter
# from youtube_transcript_api.formatters import SRTFormatter

# app = FastAPI()

# class TranscriptRequest(BaseModel):
#     video_id: str

# @app.post("/transcript")
# async def get_transcript(data: TranscriptRequest):
#     try:
#         transcript = YouTubeTranscriptApi.get_transcript(data.video_id, languages=['en'])
#         formatter = SRTFormatter()
#         formatted = formatter.format_transcript(transcript)
#         return {"transcript": formatted}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

#====================

# @app.post("/transcript")
# async def get_transcript(data: TranscriptRequest):
#     try:
#         transcript = YouTubeTranscriptApi.get_transcript(data.video_id, languages=['en'])
#         formatter = TextFormatter()
#         clean_text = formatter.format_transcript(transcript)
#         return {"transcript": clean_text}
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))


