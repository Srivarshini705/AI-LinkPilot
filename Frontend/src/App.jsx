import { useState } from "react";
import "./App.css";

function App() {
  const [domain, setDomain] = useState("");
  const [topic, setTopic] = useState("");
  const [numberOfPosts, setNumberOfPosts] = useState(1);

  const [generatedPost, setGeneratedPost] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [postText, setPostText] = useState("");
  const [imagePrompt, setImagePrompt] = useState("");
  const [isPosting, setIsPosting] = useState(false);
  const [postResult, setPostResult] = useState(null);
  const [isListening, setIsListening] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // ==========================================
  // VOICE INPUT
  // ==========================================

  const startVoiceInput = () => {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert(
        "Speech recognition is not supported in this browser. Please use Google Chrome."
      );
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      const transcript =
        event.results[0][0].transcript;

      setTopic((previous) => {
        if (previous.trim()) {
          return previous + " " + transcript;
        }

        return transcript;
      });
    };

    recognition.onerror = (event) => {
      console.error(
        "Speech recognition error:",
        event.error
      );

      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
  };

  // ==========================================
  // GENERATE POST
  // ==========================================

  const generatePost = async () => {
    if (!domain.trim()) {
      alert("Please enter your domain or industry.");
      return;
    }

    if (!topic.trim()) {
      alert("Please enter a topic or use voice input.");
      return;
    }

    setIsGenerating(true);

    try {
      /*
       * Backend API will be connected here.
       *
       * Expected backend endpoint:
       *
       * POST http://127.0.0.1:8000/generate-post
       *
       * Body:
       * {
       *   domain: "...",
       *   topic: "...",
       *   number_of_posts: 1
       * }
       */

      const response = await fetch(
        "http://127.0.0.1:8000/generate-post",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            domain: domain,
            topic: topic,
            number_of_posts: Number(numberOfPosts),
          }),
        }
      );

      if (!response.ok) {
        throw new Error(
          "Backend server returned an error."
        );
      }

      const data = await response.json();

      const post =
        data.post ||
        data.generated_post ||
        "No post was returned by the backend.";

      setGeneratedPost(post);
      setPostText(post);
    } catch (error) {
      console.error(error);

      alert(
        "Backend is not connected yet. We will connect the FastAPI backend in the next step."
      );
    } finally {
      setIsGenerating(false);
    }
  };

  // ==========================================
  // PUBLISH
  // ==========================================

  const publishPost = async (event) => {
    event.preventDefault();

    if (!postText.trim()) {
      setPostResult({
        type: "error",
        message: "Please enter the LinkedIn post text.",
      });
      return;
    }

    setIsPosting(true);
    setPostResult(null);

    try {
      const response = await fetch("http://127.0.0.1:8000/post", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          post_text: postText,
          image_prompt: imagePrompt || null,
        }),
      });

      const responseText = await response.text();
      let responseData = responseText;

      if (responseText) {
        try {
          responseData = JSON.parse(responseText);
        } catch {
          responseData = responseText;
        }
      }

      const message =
        typeof responseData === "string"
          ? responseData
          : JSON.stringify(responseData, null, 2);

      if (!response.ok) {
        throw new Error(
          message || `Request failed with status ${response.status}.`
        );
      }

      setPostResult({
        type: "success",
        message: message || "Post submitted successfully.",
      });
    } catch (error) {
      console.error(error);
      setPostResult({
        type: "error",
        message:
          error instanceof Error
            ? error.message
            : "Unable to post to LinkedIn.",
      });
    } finally {
      setIsPosting(false);
    }
  };

  return (
    <div className="app">

      {/* =====================================
          HEADER
      ====================================== */}

      <header className="header">

        <div className="logo-section">

          <div className="logo-icon">
            LP
          </div>

          <div>
            <h1>LinkPilot AI</h1>

            <p>
              AI-Powered LinkedIn Assistant
            </p>
          </div>

        </div>

        <div className="status">
          <span className="status-dot"></span>
          AI Ready
        </div>

      </header>


      {/* =====================================
          MAIN
      ====================================== */}

      <main className="main-container">

        {/* LEFT SIDE */}

        <section className="input-card">

          <div className="card-header">

            <div>
              <h2>Create LinkedIn Post</h2>

              <p>
                Enter your idea or use your voice
                to create an engaging LinkedIn post.
              </p>
            </div>

            <span className="sparkle">
              ✨
            </span>

          </div>


          {/* DOMAIN */}

          <div className="form-group">

            <label>
              Domain / Industry
            </label>

            <input
              type="text"
              placeholder="e.g. Software Development"
              value={domain}
              onChange={(event) =>
                setDomain(event.target.value)
              }
            />

          </div>


          {/* TOPIC */}

          <div className="form-group">

            <div className="label-row">

              <label>
                What do you want to post about?
              </label>

              <span>
                {topic.length}/1000
              </span>

            </div>


            <div className="topic-container">

              <textarea
                placeholder="Tell LinkPilot what you want to post about..."
                value={topic}
                maxLength={1000}
                onChange={(event) =>
                  setTopic(event.target.value)
                }
              />

              <button
                className={`voice-button ${
                  isListening ? "listening" : ""
                }`}
                onClick={startVoiceInput}
                title="Use voice input"
              >

                {isListening ? "🔴" : "🎤"}

              </button>

            </div>


            {isListening && (
              <div className="listening-text">
                🎙️ Listening... Speak now
              </div>
            )}

          </div>


          {/* NUMBER OF POSTS */}

          <div className="form-group">

            <label>
              Number of posts
            </label>

            <select
              value={numberOfPosts}
              onChange={(event) =>
                setNumberOfPosts(
                  Number(event.target.value)
                )
              }
            >

              <option value={1}>1 Post</option>
              <option value={2}>2 Posts</option>
              <option value={3}>3 Posts</option>
              <option value={4}>4 Posts</option>
              <option value={5}>5 Posts</option>

            </select>

          </div>


          {/* GENERATE */}

          <button
            className="generate-button"
            onClick={generatePost}
            disabled={isGenerating}
          >

            {isGenerating ? (
              <>
                <span className="spinner"></span>
                Generating...
              </>
            ) : (
              <>
                ✨ Generate LinkedIn Post
              </>
            )}

          </button>

        </section>


        {/* RIGHT SIDE */}

        <section className="preview-card">

          <div className="preview-header">

            <div>

              <h2>
                LinkedIn Preview
              </h2>

              <p>
                Preview and edit your AI-generated
                post before publishing.
              </p>

            </div>

            <div className="linkedin-icon">
              in
            </div>

          </div>


          {/* EMPTY STATE */}

          {!generatedPost && (
            <div className="empty-state">

              <div className="empty-icon">
                ✨
              </div>

              <h3>
                Your post will appear here
              </h3>

              <p>
                Enter a topic and click
                <strong>
                  {" "}
                  Generate LinkedIn Post
                </strong>
                .
              </p>

            </div>
          )}


          {/* GENERATED POST */}

          {generatedPost && (
            <div className="post-preview">

              <div className="profile-row">

                <div className="profile-avatar">
                  U
                </div>

                <div>

                  <h3>
                    Your LinkedIn Profile
                  </h3>

                  <span>
                    Just now · 🌐
                  </span>

                </div>

              </div>


              {isEditing ? (

                <textarea
                  className="edit-post"
                  value={generatedPost}
                  onChange={(event) => {
                    setGeneratedPost(
                      event.target.value
                    );
                    setPostText(event.target.value);
                  }}
                />

              ) : (

                <div className="post-content">

                  {generatedPost
                    .split("\n")
                    .map((line, index) => (
                      <p key={index}>
                        {line || "\u00A0"}
                      </p>
                    ))}

                </div>

              )}


              <div className="post-actions">

                <button
                  className="edit-button"
                  onClick={() =>
                    setIsEditing(!isEditing)
                  }
                >

                  {isEditing
                    ? "✓ Save Edit"
                    : "✏️ Edit"}

                </button>


              </div>

            </div>
          )}

          <form className="publish-form" onSubmit={publishPost}>
            <div className="form-group">
              <label htmlFor="post-text">
                LinkedIn post text
              </label>
              <textarea
                id="post-text"
                className="publish-textarea"
                placeholder="Write or paste the LinkedIn post you want to publish..."
                value={postText}
                onChange={(event) => setPostText(event.target.value)}
              />
            </div>

            <div className="form-group">
              <label htmlFor="image-prompt">
                Image prompt <span className="optional-label">(optional)</span>
              </label>
              <input
                id="image-prompt"
                type="text"
                placeholder="Describe an image to accompany your post"
                value={imagePrompt}
                onChange={(event) => setImagePrompt(event.target.value)}
              />
            </div>

            <button
              className="post-to-linkedin-button"
              type="submit"
              disabled={isPosting}
            >
              {isPosting ? (
                <>
                  <span className="spinner"></span>
                  Posting...
                </>
              ) : (
                "🚀 Post to LinkedIn"
              )}
            </button>

            {postResult && (
              <div
                className={`post-result ${postResult.type}`}
                role="status"
                aria-live="polite"
              >
                <strong>
                  {postResult.type === "success" ? "Success" : "Error"}
                </strong>
                <pre>{postResult.message}</pre>
              </div>
            )}
          </form>

        </section>

      </main>


      {/* =====================================
          FOOTER
      ====================================== */}

      <footer>

        <p>
          LinkPilot AI • Create smarter.
          Publish faster.
        </p>

      </footer>

    </div>
  );
}

export default App;