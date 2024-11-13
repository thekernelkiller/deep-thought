import asyncio
import aiohttp
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from typing import Dict, Any, List
import os

os.makedirs("gemini_results", exist_ok=True)

async def write_to_markdown(file_name: str, content: str) -> None:
    """Write content to a new markdown file serially if file exists."""
    base_name, ext = os.path.splitext(file_name)
    counter = 1
    new_file_name = file_name
    
    while os.path.exists(os.path.join("gemini_results", new_file_name)):
        new_file_name = f"{base_name}_{counter}{ext}"
        counter += 1
    
    with open(os.path.join("gemini_results", new_file_name), "w") as f:
        f.write(content)


SERPER_API_KEY = os.getenv("SERPER_API_KEY")
genai.configure(api_key=os.environ["API_KEY"])

generation_config = {
  "temperature": 0.7,
  "top_p": 0.95,
  "max_output_tokens": 1024,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash-8b",
  generation_config=generation_config,
  safety_settings= {
      HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
      HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
      HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
      HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE
  }
)


PERSONALIZED_PROMPT = """
You are a warm, intelligent, and well-read individual with expertise spanning multiple disciplines, including computer science, engineering, psychology, history, art, religious studies, philosophy, mathematics, literature, and neuroscience.

For casual greetings or expressions (like "hi", "hello", "thanks", "thank you", "bye", etc.):
- Respond naturally and warmly, like a friendly conversation
- Keep it short and personal
- Don't add references or links
- Match the user's tone and energy

For substantive questions or discussions:
1. Maintain a conversational yet intellectual tone, as if having a deep discussion with a peer
2. Let your thoughts flow naturally, avoiding rigid structures
3. Draw from relevant disciplines to enrich the discussion
4. Use analogies and examples to make complex ideas more accessible
5. Pose thoughtful questions to encourage reflection
6. Offer perspectives that promote critical thinking
7. Conclude with an engaging question that invites further discussion

Remember to:
- Stay warm and personable throughout
- Match the depth and complexity of your response to the user's question
- Only include references and links for substantive discussions
- Keep the conversation flowing naturally

Current conversation context: {history}
Current question: {question}
"""
    
def get_gemini_response(prompt: str, history: list = None) -> str:
    """Get a response from Gemini API using gemini-1.5-flash model."""
    try:
        # Convert history to the format Gemini expects
        chat = model.start_chat()
        
        if history:
            for msg in history:
                if msg["role"] == "user":
                    chat.send_message(msg["content"])
                # Skip assistant messages as they're handled automatically
        
        response = chat.send_message(prompt)
        return response.text

    except Exception as e:
        print(f"Error in Gemini API call: {e}")
        return f"Error: {str(e)}"

async def search_google(query: str) -> Dict[str, Any]:
    """Perform a Google search using the Serper API."""
    url = "https://google.serper.dev/search"
    payload = {"q": query}
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    headers = {k: v for k, v in headers.items() if k is not None and v is not None}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            return await response.json()

async def find_relevant_links(response: str) -> List[Dict[str, str]]:
    """Find relevant links based on the response."""
    topics_prompt = f"""
    Given the following response, extract 3-5 key topics or concepts that would benefit from additional references:

    {response}

    Please list the topics or concepts, one per line.
    """
    topics = get_gemini_response(topics_prompt).strip().split('\n')

    relevant_links = []
    for topic in topics:
        search_results = await search_google(f"{topic} scholarly articles")
        organic_results = search_results.get('organic', [])
        
        for result in organic_results:
            if 'quora.com' not in result['link'] and 'poetsandquants.com' not in result['link']:
                relevant_links.append({
                    'topic': topic,
                    'title': result['title'],
                    'link': result['link'],
                    'snippet': result['snippet']
                })
                break  # Only take the first relevant result for each topic

    return relevant_links

async def chat_companion(user_input: str, history: list = None) -> str:
    """Main function to process user input and generate a response."""
    try:
        # Check if input is a casual greeting
        casual_inputs = ["hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye", "good morning", "good evening"]
        is_casual = any(user_input.lower().strip() in greeting for greeting in casual_inputs)
        
        # Generate the main response with history context
        main_response = get_gemini_response(
            PERSONALIZED_PROMPT.format(
                question=user_input,
                history=str(history) if history else "No previous context"
            ), 
            history=history
        )
        
        # For casual interactions, return the response directly
        if is_casual:
            return main_response
            
        # For substantive questions, continue with reference enhancement
        relevant_links = await find_relevant_links(main_response)
        
        # Format the relevant links for better readability
        links_text = "\n".join([
            f"- Topic: {link['topic']}\n  Title: {link['title']}\n  URL: {link['link']}\n"
            for link in relevant_links
        ])

        # Compile the results
        compilation_prompt = f"""
        Enhance this response with the provided references:

        Response: {main_response}

        Available references:
        {links_text}

        Instructions:
        1. Integrate these references naturally into the text using markdown links
        2. Use format: [relevant text](URL)
        3. Keep the conversational tone
        4. Don't add a separate references section
        """
        
        final_response = get_gemini_response(compilation_prompt)
        return final_response

    except Exception as e:
        print(f"An error occurred: {e}")
        return f"I apologize, but an error occurred: {str(e)}"