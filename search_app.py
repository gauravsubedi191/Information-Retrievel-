import streamlit as st
import streamlit.components.v1 as components
from search_core import load_index, rank
from classifier.predict import classify  # 🔥 import classifier

# --- Page Config ---
st.set_page_config(page_title="Information Retrieval Search Engine", page_icon="📚", layout="wide")

# --- Sidebar Navigation ---
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["🔍 Search Engine", "🧠 Document Classifier"])

# ------------------ SEARCH ENGINE PAGE ------------------
if page == "🔍 Search Engine":

    # --- Custom CSS for style and animation ---
    st.markdown("""
        <style>
        .main-title {
            text-align: center;
            font-size: 1.8rem;
            font-family: 'Segoe UI',sans-serif;
            color: #3066be;
            margin-bottom: 0.2em;
            font-weight: 700;
            letter-spacing: 2px;
        }
        .subtitle {
            text-align: center;
            color: #555;
            font-size: 1.1rem;
            margin-bottom: 20px;
        }
        .search-card {
            background: #eaf0fb;
            border-radius: 16px;
            box-shadow: 0 4px 12px #e0eafc;
            padding: 2.5rem 1.5rem 1.5rem 1.5rem;
            margin-bottom: 1.5rem;
            animation: fadeInDown 0.7s;
        }
        .result-card {
            background: #fff;
            border-radius: 12px;
            box-shadow: 0 2px 8px #e0eafc;
            padding: 1.5rem 1.2rem;
            margin-bottom: 1.2rem;
            transition: box-shadow 0.3s;
            animation: fadeInUp 0.6s;
            cursor: pointer;
        }
        .result-card:hover {
            box-shadow: 0 6px 24px #b3cdf6;
            transform: scale(1.02);
            border: 2px solid #3066be;
        }
        .result-title {
            font-size: 1.25rem;
            font-weight: 700;
            color: #20509e;
            margin-bottom: 0.3rem;
            text-decoration: none;
        }
        .chip {
            display: inline-block;
            padding: 5px 14px;
            font-size: 0.97rem;
            margin-right: 8px;
            background: #f0f7ff;
            border-radius: 16px;
            color: #3066be;
            font-weight: 600;
        }
        .authors {
            color: #444;
            font-size: 1rem;
            margin-bottom: 8px;
        }
        .abstract {
            color: #333;
            font-size: 1rem;
            margin-top: 7px;
            animation: fadeIn 1.2s;
        }
        .filter-bar {
            background: #f7fafd;
            border-radius: 12px;
            padding: 1rem;
            margin-bottom: 1rem;
            box-shadow: 0 2px 8px #e0eafc;
            display: flex;
            gap: 2rem;
            align-items: center;
            justify-content: center;
            animation: fadeInRight 0.8s;
        }
        @keyframes fadeInDown {
            from { opacity: 0; transform: translateY(-30px);}
            to { opacity: 1; transform: translateY(0);}
        }
        @keyframes fadeInUp {
            from { opacity: 0; transform: translateY(30px);}
            to { opacity: 1; transform: translateY(0);}
        }
        @keyframes fadeInRight {
            from { opacity: 0; transform: translateX(40px);}
            to { opacity: 1; transform: translateX(0);}
        }
        @keyframes fadeIn {
            from { opacity: 0;}
            to { opacity: 1;}
        }
        .popup-bg {
            position: fixed;
            top:0; left:0; width:100vw; height:100vh;
            background: rgba(48,102,190,0.13);
            z-index:99;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .popup-card {
            background: #fff;
            border-radius: 20px;
            box-shadow: 0 8px 40px #20509e57;
            padding: 2rem 2.2rem 1.5rem 2.2rem;
            max-width: 540px;
            min-width: 320px;
            z-index:100;
            animation: fadeIn 0.5s;
        }
        .popup-close {
            float:right;
            font-size: 1.8rem;
            color: #3066be;
            cursor: pointer;
            margin-top: -10px;
            margin-right: -8px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- Title and Subtitle ---
    st.markdown("<div class='main-title'>📚 Information Retrieval Search Engine</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Vertical search over publications by School of Economics, Finance and Accounting members on Pure Portal.</div>", unsafe_allow_html=True)

    # --- Search Bar ---

    col_search, col_btn = st.columns([6, 1], gap="large")
    with col_search:
        q = st.text_input(
            "🔍 Search publications",
            placeholder="Type keywords, author, title, etc.",
            key="search_query",
            label_visibility="hidden"
        )
    with col_btn:
        # Add some spacing to align the button with the text input
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("❌ Clear"):
            # Delete the session state key to reset the widget
            if 'search_query' in st.session_state:
                del st.session_state['search_query']
            st.rerun()


    # --- Filter Bar ---
    st.markdown("<div class='filter-bar'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        yfrom = st.number_input("📅 From Year", min_value=1900, max_value=2100, value=2010, step=1)
    with col2:
        yto = st.number_input("📅 To Year", min_value=1900, max_value=2100, value=2100, step=1)
    with col3:
        score_min = st.slider("⭐ Min. Score", min_value=0.0, max_value=1.0, value=0.0, step=0.01)
    st.markdown("</div>", unsafe_allow_html=True)

    # --- Load Index ---
    idx_path = 'data/index.json'
    postings_path = 'data/postings.json'

    try:
        meta, postings = load_index(idx_path, postings_path)
        ready = True
    except Exception as e:
        ready = False
        st.warning('⚠️ Index not found. Please run the crawler and indexer first.')

    # --- Infinite Scroll State ---
    if "loaded_count" not in st.session_state:
        st.session_state.loaded_count = 15
    if "popup_data" not in st.session_state:
        st.session_state.popup_data = None

    def show_popup(pub):
        st.session_state.popup_data = pub
    def close_popup():
        st.session_state.popup_data = None

    # --- Search Results ---
    if ready and q.strip():
        with st.spinner("🔎 Searching..."):
            all_results = rank(meta, postings, q, topk=99999, year_from=int(yfrom), year_to=int(yto))
            all_results = [r for r in all_results if r['score'] >= score_min]

        total_results = len(all_results)
        st.markdown(f"<h4 style='color:#20509e;margin-bottom:1rem;'>{total_results} results found</h4>", unsafe_allow_html=True)
        loaded_count = st.session_state.loaded_count

        show_results = all_results[:loaded_count]
        for idx, r in enumerate(show_results):
            year = r['year'] if r['year'] is not None else 'n.d.'
            card_key = f"resultcard_{idx}"
            st.markdown(
                f"""
                <div class="result-card" onclick="window.dispatchEvent(new CustomEvent('popup_{card_key}'));">
                    <a href="{r['pub_url']}" target="_blank" class="result-title">{r['title']}</a>
                    <div>
                        <span class="chip">📅 {year}</span>
                        <span class="chip">⭐ {r['score']:.2f}</span>
                    </div>
                    <div class="authors">
                        <b>👤 Authors:</b> {', '.join(a['name'] for a in r['authors']) if r['authors'] else 'N/A'}
                    </div>
                    {'<div class="abstract">' + r['abstract'] + '</div>' if r.get('abstract') else ''}
                </div>
                """,
                unsafe_allow_html=True
            )
            components.html(f"""
            <script>
            window.addEventListener("popup_{card_key}", function() {{
                window.parent.postMessage({{"popup": "{card_key}"}}, "*");
            }});
            </script>
            """, height=0)

            if st.button("🔎 View Details", key=f"popupbtn_{card_key}"):
                show_popup(r)

        if loaded_count < total_results:
            if st.button("Load more results"):
                st.session_state.loaded_count += 15
                st.experimental_rerun()

        if st.session_state.popup_data is not None:
            pub = st.session_state.popup_data
            year = pub['year'] if pub['year'] is not None else 'n.d.'
            authors = ', '.join(a['name'] for a in pub['authors']) if pub['authors'] else 'N/A'
            abstract = pub.get('abstract', 'No abstract available.')
            components.html(f"""
            <div class="popup-bg" onclick="window.parent.postMessage({{popup_close: true}}, '*');">
                <div class="popup-card" onclick="event.stopPropagation();">
                    <span class="popup-close" onclick="window.parent.postMessage({{popup_close: true}}, '*');">&times;</span>
                    <h2 style="color:#20509e;">{pub['title']}</h2>
                    <p><b>Year:</b> {year} &nbsp; <b>Score:</b> {pub['score']:.2f}</p>
                    <p><b>Authors:</b> {authors}</p>
                    <p style="margin-top:18px;">{abstract}</p>
                    <p style='margin-top:16px;'><a href="{pub['pub_url']}" target="_blank" style="color:#3066be;">Open publication ↗</a></p>
                </div>
            </div>
            """, height=400)
            if st.button("Close", key="popup_close_btn"):
                close_popup()
                st.experimental_rerun()
    elif ready:
        st.info("💡 Enter a search query above to find publications.")

# ------------------ DOCUMENT CLASSIFIER PAGE ------------------
elif page == "🧠 Document Classifier":
    st.title("🧠 Document Classifier")
    st.write("Upload or paste text and classify it into categories (e.g., Politics, Business, Health).")

    choice = st.radio("Choose input method:", ["✍️ Paste Text", "📂 Upload File"])

    text = ""
    if choice == "✍️ Paste Text":
        text = st.text_area("Enter text to classify:", height=200)
    else:
        uploaded_file = st.file_uploader("Upload a .txt file", type=["txt"])
        if uploaded_file is not None:
            text = uploaded_file.read().decode("utf-8")
            st.text_area("Preview:", text, height=200)

    if st.button("Classify") and text.strip():
        with st.spinner("Classifying..."):
            prediction = classify(text)
        st.success(f"Predicted Category: **{prediction}**")
