import React, { useState, useRef, useEffect } from "react";
import styles from "./separation_status.module.css";
import axios from "axios";
import WaveSurfer from "wavesurfer.js";
import { Button } from "antd";
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  DownloadOutlined,
} from "@ant-design/icons";

function Separation_Status({ filename }) {
  const waveformVocalRef = useRef(null);
  const waveformInstrumRef = useRef(null);
  const [audioUrls, setAudioUrls] = useState({ vocal: "", instrum: "" });
  const [status, setStatus] = useState("");
  const [isVocalLoaded, setIsVocalLoaded] = useState(false);
  const [isInstrumLoaded, setIsInstrumLoaded] = useState(false);
  const [isPlayingVocal, setIsPlayingVocal] = useState(false);
  const [isPlayingInstrum, setIsPlayingInstrum] = useState(false);

  useEffect(() => {
    const intervalId = setInterval(async () => {
      const requestData = {
        user_id: "111",
        artist: "lee",
        filename: filename,
      };

      const response = await axios.post(
        "http://localhost:5000/download",
        requestData
      );

      setStatus(response.data.status);
      if (response.data.status === "Completed") {
        setAudioUrls({
          vocal: response.data.vocal,
          instrum: response.data.instrum,
        });

        clearInterval(intervalId);
      }
    }, 30000);

    return () => clearInterval(intervalId);
  }, [filename]);

  useEffect(() => {
    if (status === "Completed") {
      waveformVocalRef.current = WaveSurfer.create({
        container: "#waveform-vocal",
        waveColor: "violet",
        progressColor: "purple",
      });

      waveformInstrumRef.current = WaveSurfer.create({
        container: "#waveform-instrum",
        waveColor: "green",
        progressColor: "darkgreen",
      });

      waveformVocalRef.current.load(audioUrls.vocal);
      waveformInstrumRef.current.load(audioUrls.instrum);

      waveformVocalRef.current.on("ready", () => setIsVocalLoaded(true));
      waveformInstrumRef.current.on("ready", () => setIsInstrumLoaded(true));
      waveformVocalRef.current.on("play", () => setIsPlayingVocal(true));
      waveformVocalRef.current.on("pause", () => setIsPlayingVocal(false));
      waveformVocalRef.current.on("finish", () => setIsPlayingVocal(false));
      waveformInstrumRef.current.on("play", () => setIsPlayingInstrum(true));
      waveformInstrumRef.current.on("pause", () => setIsPlayingInstrum(false));
      waveformInstrumRef.current.on("finish", () => setIsPlayingInstrum(false));
    }

    return () => {
      if (
        waveformVocalRef.current &&
        typeof waveformVocalRef.current.destroy === "function"
      ) {
        waveformVocalRef.current.destroy();
      }
      if (
        waveformInstrumRef.current &&
        typeof waveformInstrumRef.current.destroy === "function"
      ) {
        waveformInstrumRef.current.destroy();
      }
    };
  }, [status, audioUrls.vocal, audioUrls.instrum]);

  const togglePlayPause = (waveformRef, isLoaded) => {
    if (isLoaded && waveformRef.current) {
      waveformRef.current.playPause();
    }
  };

  return (
    <div>
      <div className={styles.StatusButton}>
        <h4 className={styles.StatusText}>
          Separation을 수행하는데 3분정도의 시간이 걸립니다
        </h4>
        {status === "Completed" && (
          <>
            <div id="waveform-vocal" ref={waveformVocalRef}></div>
            <Button
              icon={
                isPlayingVocal ? (
                  <PauseCircleOutlined />
                ) : (
                  <PlayCircleOutlined />
                )
              }
              className={styles.PlayPause}
              onClick={() => togglePlayPause(waveformVocalRef, isVocalLoaded)}
            >
              {isPlayingVocal ? "Pause" : "Play"}
            </Button>
            <Button
              icon={<DownloadOutlined />}
              className={styles.Download}
              href={audioUrls.vocal}
              download
            >
              Download
            </Button>

            <div id="waveform-instrum" ref={waveformInstrumRef}></div>
            <Button
              icon={
                isPlayingInstrum ? (
                  <PauseCircleOutlined />
                ) : (
                  <PlayCircleOutlined />
                )
              }
              className={styles.PlayPause}
              onClick={() =>
                togglePlayPause(waveformInstrumRef, isInstrumLoaded)
              }
            >
              {isPlayingInstrum ? "Pause" : "Play"}
            </Button>
            <Button
              icon={<DownloadOutlined />}
              className={styles.Download}
              href={audioUrls.instrum}
              download
            >
              Download
            </Button>
          </>
        )}
      </div>
    </div>
  );
}

export default Separation_Status;
