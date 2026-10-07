from flask import Flask, render_template, jsonify
import os
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)


# =====================================================
# THINGSPEAK SETTINGS
# =====================================================

CHANNEL_ID = os.environ.get("THINGSPEAK_CHANNEL_ID")
READ_API_KEY = os.environ.get("THINGSPEAK_READ_API_KEY")


# =====================================================
# GET THINGSPEAK DATA
# =====================================================

def get_thingspeak_data():

    missing_variables = []

    if not CHANNEL_ID:
        missing_variables.append("THINGSPEAK_CHANNEL_ID")

    if not READ_API_KEY:
        missing_variables.append("THINGSPEAK_READ_API_KEY")

    if missing_variables:
        raise RuntimeError(
            "Missing required environment variable(s): "
            + ", ".join(missing_variables)
        )

    thingspeak_url = (
        f"https://api.thingspeak.com/channels/"
        f"{CHANNEL_ID}/feeds.json"
    )

    params = {
        "api_key": READ_API_KEY,
        "results": 30
    }

    response = requests.get(
        thingspeak_url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    return response.json()


# =====================================================
# CONVERT VALUE
# =====================================================

def safe_float(value):

    try:
        return float(value)

    except:
        return 0.0


# =====================================================
# AI / ML STYLE PANEL ANALYSIS
# =====================================================

def analyze_panel(
    voltage,
    current,
    power,
    temperature,
    humidity,
    dust
):

    score = 100

    reasons = []


    # =================================================
    # VOLTAGE
    # =================================================

    if voltage < 0.5:

        score -= 35

        reasons.append(
            "Very low panel voltage"
        )

    elif voltage < 1.0:

        score -= 20

        reasons.append(
            "Low panel voltage"
        )


    # =================================================
    # DUST
    # =================================================

    if dust > 2000:

        score -= 25

        reasons.append(
            "High dust accumulation"
        )

    elif dust > 1000:

        score -= 10

        reasons.append(
            "Moderate dust level"
        )


    # =================================================
    # TEMPERATURE
    # =================================================

    if temperature > 70:

        score -= 25

        reasons.append(
            "Critical temperature"
        )

    elif temperature > 55:

        score -= 12

        reasons.append(
            "High temperature"
        )


    # =================================================
    # POWER
    # =================================================

    if voltage > 1.0 and power < 0.2:

        score -= 15

        reasons.append(
            "Low power generation"
        )


    # =================================================
    # LIMIT
    # =================================================

    score = max(
        0,
        min(
            100,
            score
        )
    )


    # =================================================
    # STATUS
    # =================================================

    if score >= 80:

        status = "HEALTHY"

    elif score >= 50:

        status = "WARNING"

    else:

        status = "CRITICAL"


    if not reasons:

        reasons.append(
            "Panel operating within normal range"
        )


    return {
        "score": score,
        "status": status,
        "reasons": reasons
    }


# =====================================================
# DASHBOARD
# =====================================================

@app.route("/")
def dashboard():

    return render_template(
        "index.html"
    )


# =====================================================
# API
# =====================================================

@app.route("/api/data")
def api_data():

    try:

        data =get_thingspeak_data()

        feeds =data.get(
                "feeds",
                []
            )


        if not feeds:

            return jsonify({
                "online": False,
                "message":
                    "No ThingSpeak data"
            })


        latest =feeds[-1]


        voltage =safe_float(
                latest.get(
                    "field1"
                )
            )


        current =safe_float(
                latest.get(
                    "field2"
                )
            )


        power =safe_float(
                latest.get(
                    "field3"
                )
            )


        temperature =safe_float(
                latest.get(
                    "field4"
                )
            )


        humidity =safe_float(
                latest.get(
                    "field5"
                )
            )


        dust =safe_float(
                latest.get(
                    "field6"
                )
            )


        servo =safe_float(
                latest.get(
                    "field7"
                )
            )


        health =safe_float(
                latest.get(
                    "field8"
                )
            )


        # =================================================
        # AI ANALYSIS
        # =================================================

        analysis =analyze_panel(
                voltage,
                current,
                power,
                temperature,
                humidity,
                dust
            )


        # =================================================
        # HISTORY
        # =================================================

        history = []


        for feed in feeds:

            history.append({

                "time":
                    feed.get(
                        "created_at",
                        ""
                    ),

                "voltage":
                    safe_float(
                        feed.get(
                            "field1"
                        )
                    ),

                "current":
                    safe_float(
                        feed.get(
                            "field2"
                        )
                    ),

                "power":
                    safe_float(
                        feed.get(
                            "field3"
                        )
                    ),

                "temperature":
                    safe_float(
                        feed.get(
                            "field4"
                        )
                    ),

                "dust":
                    safe_float(
                        feed.get(
                            "field6"
                        )
                    )
            })


        # =================================================
        # DATA AGE
        # =================================================

        timestamp =latest.get(
                "created_at"
            )


        data_status ="LIVE"


        if timestamp:

            try:

                dt =datetime.fromisoformat(
                        timestamp.replace(
                            "Z",
                            "+00:00"
                        )
                    )


                age =(
                        datetime.now(
                            timezone.utc
                        ) - dt
                    ).total_seconds()


                if age > 60:

                    data_status ="DATA DELAY"


                if age > 180:

                    data_status ="ESP32 OFFLINE"

            except:

                pass


        return jsonify({

            "online": True,

            "data_status":
                data_status,

            "timestamp":
                timestamp,

            "voltage":
                voltage,

            "current":
                current,

            "power":
                power,

            "temperature":
                temperature,

            "humidity":
                humidity,

            "dust":
                dust,

            "servo":
                servo,

            "health":
                health,

            "analysis":
                analysis,

            "history":
                history
        })


    except Exception as e:

        return jsonify({

            "online": False,

            "message":
                str(e)
        })


# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )