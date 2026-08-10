import json
import os

import streamlit as st

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


TOKEN_FILE = "auth/oauth_token.json"


def get_google_credentials():

    token_data = None

    # ==========================================================
    # MODE LOCAL
    # ==========================================================

    if os.path.exists(TOKEN_FILE):

        with open(
            TOKEN_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            token_data = json.load(f)

    # ==========================================================
    # MODE STREAMLIT CLOUD
    # ==========================================================

    else:

        try:

            if "oauth_token" in st.secrets:

                token_data = dict(
                    st.secrets["oauth_token"]
                )

        except Exception as e:

            st.error(
                f"❌ Gagal membaca Streamlit Secrets: {e}"
            )

            raise

    # ==========================================================
    # TOKEN TIDAK DITEMUKAN
    # ==========================================================

    if not token_data:

        raise Exception(
            "OAuth token tidak ditemukan. "
            "Pastikan auth/oauth_token.json tersedia "
            "atau [oauth_token] sudah diisi di Streamlit Secrets."
        )

    # ==========================================================
    # GOOGLE CREDENTIALS
    # ==========================================================

    credentials = Credentials(

        token=token_data.get("token"),

        refresh_token=token_data.get(
            "refresh_token"
        ),

        token_uri=token_data.get(
            "token_uri",
            "https://oauth2.googleapis.com/token"
        ),

        client_id=token_data.get(
            "client_id"
        ),

        client_secret=token_data.get(
            "client_secret"
        ),

        scopes=tuple(
            token_data.get("scopes", [])
        ),

    )

    # ==========================================================
    # VALIDASI CREDENTIALS
    # ==========================================================

    if not credentials.valid:

        if credentials.expired and credentials.refresh_token:

            credentials.refresh(
                Request()
            )

        else:

            raise Exception(
                "Google OAuth credentials tidak valid "
                "dan tidak memiliki refresh token."
            )

    return credentials