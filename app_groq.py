import asyncio
import aiohttp
from groq import Groq
from typing import Dict, Any, List
import os

os.makedirs("groq_results", exist_ok=True)

async def write_to_markdown(file_name: str, content: str) -> None:
    """Write content to a new markdown file serially if file exists."""
    base_name, ext = os.path.splitext(file_name)
    counter = 1
    new_file_name = file_name
    
    while os.path.exists(os.path.join("groq_results", new_file_name)):
        new_file_name = f"{base_name}_{counter}{ext}"
        counter += 1
    
    with open(os.path.join("groq_results", new_file_name), "w") as f:
        f.write(content)


SERPER_API_KEY = os.getenv("SERPER_API_KEY")
client = Groq(
    api_key = os.getenv("GROQ_API_KEY")
)

PERSONALIZED_PROMPT = """
You are a highly intelligent and well-read individual with expertise spanning multiple disciplines, including but not limited to computer science, engineering, psychology, history, art, religious studies (bhagavadgita, quran, bible, etc.), philosophy, mathematics, literature, and neuroscience. Your task is to engage in a thoughtful, nuanced conversation on the given topic, drawing from your vast knowledge base to provide insights and perspectives.

Please adhere to the following guidelines:

1. Maintain a conversational yet intellectual tone, as if engaging in a deep discussion with a peer.
2. Be casual and informal. Understand the user's style and tone and respond in the same manner. 
2. Avoid using a structured format with explicit subsections. Instead, let your thoughts flow naturally from one idea to the next.
3. Incorporate relevant quotes, concepts, or principles from various fields to support and enrich your discussion.
4. Present a multifaceted exploration of the topic, considering psychological, philosophical, and cultural aspects where applicable.
5. Use analogies or comparisons to complex ideas from different disciplines to illuminate your points.
6. Pose thought-provoking questions throughout your response to encourage deeper reflection.
7. Avoid being prescriptive or overly suggestive. Instead, offer perspectives that prompt the individual to think critically about their situation.
8. Gradually develop your ideas, allowing for a natural progression of thought.
9. While you may draw from multiple disciplines, don't feel obligated to reference all fields of knowledge if they don't naturally fit the discussion.
10. Conclude with a thought that ties back to the original question while leaving room for further contemplation.

Respond to the following question: {question}
"""

def get_groq_response(prompt: str) -> str:
    """Get a response from Groq API."""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            # max_tokens=1100
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in Groq API call: {e}")
        return ""
    

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
    topics = get_groq_response(topics_prompt).strip().split('\n')

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

async def chat_companion(user_input: str) -> str:
    """Main function to process user input and generate a response."""
    try:
        # Generate the main response
        main_response = get_groq_response(PERSONALIZED_PROMPT.format(question=user_input))
        
        # Find relevant links based on the response
        relevant_links = await find_relevant_links(main_response)

        # Compile the results
        compilation_prompt = f"""
        You are tasked with enhancing the following response by integrating relevant scholarly references as inline Markdown links:

        Main response: {main_response}

        Relevant links:
        {relevant_links}

        Please modify the main response to include these scholarly references as inline Markdown links. 
        Use the format [anchor text](URL), where the anchor text is a natural part of the sentence, 
        not just the title of the article. The link should be placed immediately after the relevant 
        concept or quote it supports.

        For example:
        "As [recent studies have shown](https://example.com/study), neural networks can..."

        Maintain the conversational yet intellectual tone of the original response. 
        The goal is to seamlessly support the ideas presented with credible sources 
        without disrupting the overall structure and flow of the response.

        Do not add a separate references section at the end. All links should be embedded within the text.
        """
        final_response = get_groq_response(compilation_prompt)

        return final_response
    except Exception as e:
        print(f"An error occurred: {e}")
        return f"I'm sorry, but an error occurred while processing your request: {e}"

# Example usage
async def main():
    user_question_1 = "Why do i keep disappointing the people i love?"
    user_question_2 = "explain communism and capitalism within computer science."
    user_question_3 = "How should I handle myself? Campus hirings are going on and it's a tough market and on top of that, companies seem to hire candidates randomly. It's all luck and doesn't seem like it's going on with respect to skill. It's frustrating."
    user_question_4 = "why is europe worse for me than the US if i'm a techie working in india?"
    user_question_5 = "tell me about love and how is it any difference from physical / chemical attractive forces like in gravity and atoms?"
    user_question_6 = "what can we learn from APIs?"

    user_question = "is sex and temptation always as misunderstood as it is now?"

    response = await chat_companion(user_question)
    
    # Write the response to a markdown file
    await write_to_markdown("response.md", response)
    print(response)

if __name__ == "__main__":
    asyncio.run(main())