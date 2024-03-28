import { useState, useRef, useEffect } from "react";
import axios from "axios";
import WaveSurfer from "wavesurfer.js";
import { Button, Slider } from "antd";
import styles from "./mainbutton.module.css";

export default function MainButton() {
  const [inputValue, setInputValue] = useState("");
  const [audioUrl, setAudioUrl] = useState(""); // localStorage에서 값을 불러오지 않음
  const waveSurferRef = useRef(null);

  useEffect(() => {
    if (!waveSurferRef.current && document.getElementById("waveform")) {
      waveSurferRef.current = WaveSurfer.create({
        container: "#waveform",
        waveColor: "violet",
        progressColor: "purple",
        height: 80,
        barWidth: 2,
      });
    }

    if (audioUrl) {
      waveSurferRef.current.load(audioUrl); // localStorage에 저장하는 부분을 제거함
    }

    return () => {
      if (waveSurferRef.current) {
        waveSurferRef.current.destroy();
      }
    };
  }, [audioUrl]);

  const handleInputChange = (e) => {
    setInputValue(e.target.value);
  };

  const handleSearch = async () => {
    try {
      const response = await axios.get(
        "http://localhost:5000/download_youtube",
        {
          params: { input: inputValue, user_id: "123" },
        }
      );
      setAudioUrl(response.data);
    } catch (error) {
      console.error("API 호출 중 에러 발생:", error);
    }
  };

  const handleVolumeChange = (value) => {
    if (waveSurferRef.current) {
      waveSurferRef.current.setVolume(value / 100);
    }
  };

  return (
    <div className={styles.align}>
      <h5 className={styles.Text}>노래명과 가수명 또는 url을 입력해보세요</h5>
      <input
        className={styles.input}
        type="input"
        value={inputValue}
        onChange={handleInputChange}
      ></input>
      <button className={styles.SearchButton} onClick={handleSearch}>
        Search
      </button>
      {audioUrl && (
        <div className={styles.Wave}>
          <div id="waveform"></div>
          <Button
            className={styles.button}
            onClick={() => waveSurferRef.current.play()}
          >
            Play
          </Button>
          <Button
            className={styles.button}
            onClick={() => waveSurferRef.current.pause()}
          >
            Pause
          </Button>
          <Button className={styles.button} href={audioUrl} download>
            Download
          </Button>
          <Slider defaultValue={100} onAfterChange={handleVolumeChange} />
        </div>
      )}
    </div>
  );
}
