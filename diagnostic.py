import asyncio
import traceback
from app.agent import root_agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

async def main():
    print("Starting diagnostic...")
    r = Runner(agent=root_agent, session_service=InMemorySessionService(), app_name='test')
    session = await r.session_service.create_session(user_id='test', app_name='test')
    m = types.Content(role='user', parts=[types.Part.from_text(text='test')])
    try:
        async for event in r.run_async(user_id='test', session_id=session.id, new_message=m):
            print(f"Event: {event}")
    except Exception as e:
        print("Exception caught:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
