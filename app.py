import streamlit as st
from datetime import datetime
import json 
from document_ai import (analyse_document, find_risk_flags, answer_question,
                         chunk_text, get_embeddings, get_random_comparison, get_loading_fact)
from extractor import extract_text
from database import (register_user, login_user, save_document, get_documents,
                      get_document_by_id, update_document_analysis,
                      delete_document, save_chunks, get_chunks,
                      save_question, get_questions)


# ---- Page Config ----
st.set_page_config(
    page_title="Legal Document Analyser",
    page_icon="⚖️",
    layout="wide"
)

# ---- Auth gate ----
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("⚖️ Legal Document Analyser")
        st.markdown("*AI-powered contract analysis for legal professionals*")
        st.markdown("---")

        tab1, tab2 = st.tabs(["Login", "Register"])

        with tab1:
            st.subheader("🔐 Login")
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            if st.button("Login", type="primary", key="login_btn"):
                user = login_user(username, password)
                if user:
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error("Invalid useername or password.")

        with tab2:
            st.subheader("📝 Register")
            new_username = st.text_input("Choose username", key="reg_user")
            new_password = st.text_input("Choose password",type="password", key="reg_pass")
            confirm = st.text_input("Confirm password", type="password", key="reg_confirm")

            if st.button("Register", type="primary", key="reg_btn"):
                if not new_username or not new_password:
                    st.error("Please fill in all fields.")
                elif new_password != confirm:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    success = register_user(new_username, new_password)
                    if success:
                        st.success("✅ Account created. Please login.")
                    else:
                        st.error("Username already taken.")
        return False
    return True

if not check_password():
    st.stop()


# ---- Logged in - get user details ----
user = st.session_state["user"]
user_id = user["id"]
username = user["username"]


# ---- Sidebar ----
st.sidebar.title("⚖️ Legal Analyser")
st.sidebar.markdown(f"👤 **{username}**")
st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    ["📄 Analyse Document", "📁 Document History", "📖 How to Use"]
)

if page == "📄 Analyse Document":
    st.header("📄 Analyse Document")
    st.markdown("*Upload a legal document for AI-powered analysis*")

    # ---- Did You Know card ----
    if "current_summary" not in st.session_state:
        comparison = get_random_comparison()
        with st.container():
            st.markdown("### 📚 Did You Know?")
            st.markdown(f"**{comparison['topic']}**")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("🇬🇧 **UK**")
                st.info(comparison['uk'])
            with col2:
                st.markdown("🇳🇬 **Nigeria**")
                st.info(comparison['nigeria'])
            st.warning(f"🔍 **Key Difference:** {comparison['difference']}")
        st.markdown("---")


    # ---- File Upload ----
    uploaded_file = st.file_uploader(
        "Upload legal document",
        type=["pdf", "docx", "doc", "png", "jpeg", "jpg", "webp"],
        help="Supports PDF, Word documents (.docx), and photos of documents"
    )

    if uploaded_file:
        st.info(f"📎 **{uploaded_file.name}** - ready to analyse")

        if st.button("⚖️ Analyse Document", type="primary", key="analyse_btn"):

            # ---- Step 1: Extracted text ----
            with st.spinner("📖 Extracting text...."):
                extracted_text, file_type = extract_text(uploaded_file)

            if extracted_text.startswith("ERROR:"):
                st.error(extracted_text)
                st.stop()

            st.success(f"✅ Text extracted - {len(extracted_text):,} characters")

            # ---- Step 2: Save document + chunk + embed ----
            with st.spinner("💾 Saving and processing document..."):
                document_id = save_document(
                    user_id=user_id,
                    filename=uploaded_file.name,
                    file_type=file_type,
                    extracted_text=extracted_text
                )

                chunks = chunk_text(extracted_text)
                embeddings = get_embeddings(chunks)
                save_chunks(document_id, chunks, embeddings)

            st.success(f"✅ Document split into {len(chunks)} searchable chunks")

            # ---- Step 3: AI Analysis ----
            with st.spinner(f"🤖 Claude is analysing... {get_loading_fact()}"):
                summary = analyse_document(extracted_text, uploaded_file.name)
                risk_flags = find_risk_flags(extracted_text)
                update_document_analysis(
                    document_id, summary, str(risk_flags)
                )

            # ---- Store in session_state ----
            st.session_state["current_doc_id"] = document_id
            st.session_state["current_filename"] = uploaded_file.name
            st.session_state["current_summary"] = summary
            st.session_state["current_flags"] = risk_flags
            st.session_state["current_chunks"] = get_chunks(document_id)

    # ---- Display results if document analysed ----
    if "current_summary" in st.session_state:
        st.markdown()

        # ---- Summary ----
        st.subheader(f"📋 Analysis: {st.session_state['current_filename']}")
        st.markdown(st.session_state["current_summary"])

        st.markdown("---")

        # ---- Risk Flags ----
        st.subheader("🚨 Risk Flags")
        flags = st.session_state["current_flags"]

        if not flags:
            st.success("✅ No major risk terms detected.")
        else:
            st.warning(f"⚠️ {len(flags)} risk term(s) detected - review carefully")
            for flag in flags:
                with st.expander(f"🚨 {flag['term'].upper()}"):
                    st.markdown(f"**Found in context:**")
                    st.markdown(f"> {flag['context']}")

        st.markdown("---")


        # ---- Q&A ----
        st.subheader("❓ Ask About This Document")
        question = st.text_input(
            "Type your question",
            placeholder="e.g. What are thr termination conditions?",
            key="legal_question"
        )

        if st.button("Ask", type="primary", key="ask_btn"):
            if not question.strip():
                st.warning("Please type a question first.")
            else:
                with st.spinner("🤖 Searching document..."):
                    answer = answer_question(
                        question,
                        st.session_state["current_chunks"],
                        st.session_state["current_filename"]
                    )
                    save_question(
                        st.session_state["current_doc_id"],
                        user_id, question, answer
                    )

                st.markdown("**Answer:**")
                st.markdown(answer)

        # ---- Past Questions ----
        past_questions = get_questions(
            st.session_state["current_doc_id"]
        )
        if past_questions:
            st.markdown("---")
            st.subheader("📝 Previous Questions")
            for q in past_questions:
                with st.expander(f"Q: {q['question'][:60]}..."):
                    st.markdown(f"**Q:** {q['question']}")
                    st.markdown(f"**A:** {q['answer']}")
                    st.caption(q['timestamp'])

elif page == "📁 Document History":
    st.header("📁 Document History")
    st.markdown("*View and Manage your previously analysed documents*")

    documents = get_documents(user_id)

    if not documents:
        st.info("No documents analysed yet. Go to Analyse Document to get started.")
    else:
        st.markdown(f"**{len(documents)} document(s) saved**")
        st.markdown("---")

        # ---- Detail View ----
        if "viewing_doc" in st.session_state:
            doc = st.session_state["viewing_doc"]

            col1, col2 = st.columns([3, 1])
            with col1:
                if st.button("← Back to History", key="back_btn"):
                    del st.session_state["viewing_doc"]
                    st.rerun()
            with col2:
                if st.button("🗑️ Delete Document", key="delete_btn"):
                    st.session_state["confirm_delete"] = True

            if st.session_state.get("confirm_delete"):
                st.warning(
                    f"⚠️ Delete **{doc['filename']}**? "
                    f"This cannot be undone."
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Yes, delete", key="confirm_yes",
                                 type="primary"):
                        delete_document(doc["id"], user_id)
                        if st.session_state.get(
                            "current_doc_id"
                        ) == doc["id"]:
                            for key in ["current_doc_id",
                                        "current_filename",
                                        "current_summary",
                                        "current_flags",
                                        "current_chunks"
                                        ]:
                                st.session_state.pop(key, None)
                        del st.session_state["viewing_doc"]
                        del st.session_state["confirm_delete"]
                        st.success("Document deleted.")
                        st.rerun()
                with col2:
                    if st.button("Cancel", key="confirm_no"):
                        del st.session_state["confirm_delete"]
                        st.rerun()

            else:
                st.subheader(f"📄 {doc['filename']}")
                st.caption(
                    f"Type: {doc['file_type']} | "
                    f"Uploaded: {doc['upload_date']}"
                )
                st.markdown("---")

                # ---- Summary ----
                if doc.get("summary"):
                    st.subheader("📋 Analysis")
                    st.markdown(doc["summary"])
                else:
                    st.info("No analysis saved for this document.")

                st.markdown("---")

                # ---- Risk flags ----
                st.subheader("🚨 Risk Flags")
                if doc.get("risk_flags"):
                    try:
                        flags = eval(doc["risk_flags"])
                        if not flags:
                            st.success("✅ No risk terms detected.")
                        else:
                            st.warning(
                                f"⚠️ {len['flags']} risk term(s) found"
                            )
                            for flag in flags:
                                with st.expander(
                                    f"🚨 {flag['term'].upper()}"
                                ):
                                    st.markdown(f"> {flag['context']}")
                    except:
                        st.info("Risk flag data unavailable.")
                else:
                    st.info("No risk analysis saved.")

                st.markdown("---")

                # ---- Q&A ----
                st.subheader("❓ Ask About This Document")

                chunks = get_chunks(doc["id"])
                question = st.text_input(
                    "Type your question",
                    placeholder="e.g. What are the payment terms?",
                    key="history_question"
                )

                if st.button("Ask", type="primary", key="history_ask_btn"):
                    if not question.strip():
                        st.warning("Please type a question first.")
                    elif not chunks:
                        st.error(
                            "No searchable chunks found "
                            "for this document."
                        )
                    else:
                        with st.spinner("🤖 Searching document..."):
                            answer = answer_question(
                                question, chunks, doc["filename"]
                            )
                            save_question(
                                doc["id"], user_id, question, answer
                            )
                        st.markdown("**Answer:**")
                        st.markdwon(answer)

                # ---- Past Questions ----
                past = get_questions(doc["id"])
                if past:
                    st.markdown("---")
                    st.subheader("📝 Previous Questions")
                    for q in past:
                        with st.expander(
                            f"Q: {q['question'][:60]}..."
                        ):
                            st.markdown(f"**Q:** {q['question']}")
                            st.markdown(f"**A:** {q['answer']}")
                            st.caption(q['timestamp'])

        # ---- List View ----
        else:
            for i, doc in enumerate(documents):
                with st.container():
                    col1, col2, col3 = st.columns([3, 2, 1])
                    with col1:
                        icon = {
                            "pdf": "📕",
                            "docx": "📘",
                            "image": "📸"
                        }.get(doc["file_type"], "📄")
                        st.markdown(
                            f"{icon} **{doc['filename']}**"
                        )
                        st.caption(f"Uploaded: {doc['upload_date']}")
                    with col2:
                        flag_text = "⚠️ risk flags found" \
                            if doc.get("risk_flags") \
                            and doc["risk_flags"] != "[]" \
                            else "✅ No flags"
                        st.caption(flag_text)
                    with col3:
                        if st.button("View", key=f"view_{i}"):
                            st.session_state["viewing_doc"] = doc 
                            st.rerun()
                    st.markdown("---")

elif page == "📖 How to Use":
    st.header("📖 How to Use the Legal Document Analyser")
    st.markdown("*A guide for legal professionals*")

    # ---- Quick Start ----
    st.subheader("🚀 Quick Start")
    st.markdown("""
1. **Upload** your document using the Analyse Document page (in accordance to the page number)
2. **Wait** for the AI to extract text and generate analysis (30-60 seconds)
3. **Review** the executive summary, key clauses, and risk flags
4. **Ask questions** about specific clauses in the Q&A section
5. **Return** to past documents anytime via Document History
""")

    st.markdown("---")

    # ---- Supported Files ----
    with st.expander("📎 Supported File Types", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**📕 PDF**")
            st.markdown("Scanned or digital PDF contracts")
        with col2:
            st.markdown("**📘 Words Document**")
            st.markdown(".docx and .doc files from Microsoft Word")
        with col3:
            st.markdown("**📸 Photos**")
            st.markdown("JPG, PNG, WEBP - photos of paper documents")

    # ---- Photo Guide ----
    with st.expander("📸 How to Photograph a Paper Document"):
        st.markdown("""
**For best results when photopraphing paper contracts:**

✅ **Good lighting** — use natural daylight or a bright indoor light.
Avoid shadows across the page.

✅ **Flat and straight** — lay the document flat on a table.
Hold the camera directly above — not at an angle.

✅ **Close enough** — the text should fill most of the frame.
One page per photo gives the best results.

✅ **Steady hands** — tap the screen to focus before shooting.
Motion blur makes text unreadable.

✅ **Upload in order** — if photographing multiple pages,
upload them in page order. The app combines them in sequence.

❌ **Avoid:** Dark backgrounds, heavy filters, extremely crumpled pages,
or handwritten documents in very small script.
""")

    # ---- Risk Flags ----
    with st.expander("🚨 Understanding Risk Flags"):
        st.markdown("""
Risk flags highlight legal terms that commonly indicate
obligations, liabilities, or restrictions that deserve
careful attention before signing.

**Common flags and what they mean:**

| Term | Why It Matters |
|------|---------------|
| **Indemnification** | You may be liable for the other party's losses |
| **Irrevocable** | You cannot undo this agreement once signed |
| **Non-compete** | Restricts your ability to work elsewhere |
| **Perpetual** | The obligation never expires |
| **Automatic renewal** | Contract continues unless you actively cancel |
| **Sole discretion** | The other party has unchecked decision-making power |
| **Personal guarantee** | Your personal assets may be at risk |
| **Arbitration** | Disputes go to arbitration, not court |

⚠️ A risk flag does not mean the clause is unenforceable or unfair —
it means it deserves careful review by a qualified lawyer.
""")

    # ---- Q&A Tips ----
    with st.expander("❓ How to Ask Good Questions"):
        st.markdown("""
The Q&A feature searches the document for relevant sections
and uses AI to answer your specific question.

**Questions that work well:**
- "What are the termination conditions?"
- "How many days notice is required to end this contract?"
- "What are the payment terms and penalties for late payment?"
- "Which jurisdiction governs this agreement?"
- "What does the indemnification clause say?"

**Questions that work less well:**
- "Is this a good contract?" ← requires legal judgment
- "What should I do?" ← outside the app's scope
- "What does [term] mean in general?" ← the app answers from 
  the document, not general legal knowledge

**Tip:** Be specific. "What are the payment terms?" 
gets better results than "Tell me about money."
""")

    # ---- Privacy ----
    with st.expander("🔒 Privacy and Security"):
        st.markdown("""
**How your documents are stored:**

✅ Documents are stored in a private encrypted database (Supabase PostgreSQL)

✅ Your data is isolated — no other user can access your documents

✅ All database connections use SSL encryption

✅ You can delete any document permanently from Document History

**Important notice for legal professionals:**

⚠️ When you upload a document for analysis, the document text
is sent to Anthropic's Claude API for processing.
Anthropic's privacy policy governs how that data is handled.

**Recommendation:** For documents containing sensitive client information,
consider removing or redacting client names and identifying details
before uploading. The analysis works on the contract terms themselves —
not the parties' identities.

This tool is designed to assist legal professionals —
not replace client confidentiality obligations.
""")

    # ---- Limitations ----
    with st.expander("⚠️ Limitations - Please Read"):
        st.markdown("""
**This tool is an AI-powered first-pass analysis. It has real limitations:**

1. **Not legal advice** — The app identifies and flags clauses.
   It cannot tell you what legal action to take, whether to sign,
   or what a clause means for your specific legal situation.
   Always consult a qualified lawyer before acting on any analysis.

2. **Document-bound answers** — The Q&A only answers from
   the uploaded document. It cannot draw on external legal knowledge,
   case law, or legislation not present in the document.

3. **Not exhaustive** — The risk flag system detects common terms.
   It may miss unusual or jurisdiction-specific clauses.
   AI analysis is a first pass — not a replacement for full 
   legal review by a qualified professional.

4. **Image quality dependent** — Analysis of photographed documents
   depends heavily on photo quality. Blurry or poorly lit images
   may produce incomplete text extraction.

5. **AI can be wrong** — Claude is a powerful language model
   but can misinterpret complex legal language. Verify any
   AI-generated analysis against the original document.

**This tool supports your legal work — it does not replace your judgment.**
""")

    # ---- Contact ----
    st.markdown("---")
    st.markdown("**Questions or feedback?**")
    st.markdown("Contact: olanipekunwahab1@gmail.com")
    st.markdown("Built by Wahab Olanipekun · wahab16-blip.github.io")



if st.sidebar.button("Logout", key="logout_btn"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()


























































