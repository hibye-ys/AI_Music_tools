import React, { useState, useEffect, useRef } from "react";
import {
  PoweroffOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  DownloadOutlined,
} from "@ant-design/icons";
import { Button, message, Tabs } from "antd";
import WaveSurfer from "wavesurfer.js";
import axios from "axios";
import styles from "./vc_inferencetab.module.css";
import VC_InferenceCombineTab from "./VC_InferenceCombineTab";

const VC_InferenceTab = () => {
  const [loadings, setLoadings] = useState([]);
  const [audioUrl1, setAudioUrl1] = useState("");
  const [isPlaying1, setIsPlaying1] = useState(false);
  const waveformRef1 = useRef(null);
  const wavesurfer1 = useRef(null);

  const [audioUrl2, setAudioUrl2] = useState("");
  const [isPlaying2, setIsPlaying2] = useState(false);
  const waveformRef2 = useRef(null);
  const wavesurfer2 = useRef(null);

  const [audioUrlCombined, setAudioUrlCombined] = useState("");

  useEffect(() => {
    if (waveformRef1.current) {
      wavesurfer1.current = WaveSurfer.create({
        container: waveformRef1.current,
        waveColor: "purple",
        progressColor: "violet",
        cursorColor: "transparent",
        height: 200,
      });

      wavesurfer1.current.on("play", () => setIsPlaying1(true));
      wavesurfer1.current.on("pause", () => setIsPlaying1(false));
      wavesurfer1.current.on("finish", () => setIsPlaying1(false));
    }

    if (waveformRef2.current) {
      wavesurfer2.current = WaveSurfer.create({
        container: waveformRef2.current,
        waveColor: "blue",
        progressColor: "green",
        cursorColor: "transparent",
        height: 200,
      });

      wavesurfer2.current.on("play", () => setIsPlaying2(true));
      wavesurfer2.current.on("pause", () => setIsPlaying2(false));
      wavesurfer2.current.on("finish", () => setIsPlaying2(false));
    }

    return () => {
      wavesurfer1.current?.destroy();
      wavesurfer2.current?.destroy();
    };
  }, []);

  const enterLoading = async (index) => {
    setLoadings((prevLoadings) => {
      const newLoadings = [...prevLoadings];
      newLoadings[index] = true;
      return newLoadings;
    });
    const postData = {
      user_id: "111",
      artist: "lee",
      filename: "Get_Lucky.wav",
    };
    try {
      const postData = {
        user_id: "111",
        artist: "lee",
        filename: "Get_Lucky.wav",
      };

      // 첫 번째 요청 실행 및 응답 기다리기
      const response1 = await axios.post(
        "http://localhost:5000/vc_inference_check",
        postData
      );
      const audioUrl1 = response1.data;
      console.log("Response 1", response1.data);
      setAudioUrl1(audioUrl1);
      wavesurfer1.current.load(audioUrl1);

      // 두 번째 요청 실행 및 응답 기다리기
      const response2 = await axios.post(
        "http://localhost:5000/download",
        postData
      );
      const audioUrl2 = response2.data.instrum;
      console.log("Response 2", response2.data.instrum);
      setAudioUrl2(audioUrl2);
      wavesurfer2.current.load(audioUrl2);

      // 모든 요청이 완료된 후 세 번째 요청 실행
      const combine_data = {
        url1: audioUrl1,
        url2: audioUrl2,
        user_id: "111",
      };
      console.log(combine_data);
      const response3 = await axios.post(
        "http://localhost:5000/combine_inferencedAudio",
        combine_data
      );
      console.log("Combined data", response3.data);
      setAudioUrlCombined(response3.data);
    } catch (error) {
      message.error("Voice conversion failed.");
      console.error("Error:", error);
    } finally {
      setLoadings((prevLoadings) => {
        const newLoadings = [...prevLoadings];
        newLoadings[index] = false;
        return newLoadings;
      });
    }
  };

  const handlePlayPause1 = () => {
    wavesurfer1.current.playPause();
  };

  const handlePlayPause2 = () => {
    wavesurfer2.current.playPause();
  };

  const downloadAudio1 = () => {
    if (!audioUrl1) {
      message.error("No audio loaded!");
      return;
    }

    const a = document.createElement("a");
    a.href = audioUrl1;
    a.download = "downloaded_audio.wav"; // 또는 서버로부터 받은 파일 이름
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const downloadAudio2 = () => {
    if (!audioUrl2) {
      message.error("No audio loaded!");
      return;
    }

    const a = document.createElement("a");
    a.href = audioUrl2;
    a.download = "downloaded_audio_2.wav"; // 또는 서버로부터 받은 파일 이름
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const tabsItems = [
    {
      label: <div className={styles.Tabs}>Vocal/Inst</div>,
      key: "1",
      children: (
        <div className={styles.audioContainer}>
          <div
            className={styles.waveform}
            ref={waveformRef1}
            onClick={handlePlayPause1}
            style={{ cursor: "pointer" }}
          />
          {audioUrl1 && (
            <div className={styles.controls}>
              <Button
                className={styles.PlayButton}
                icon={
                  isPlaying1 ? <PauseCircleOutlined /> : <PlayCircleOutlined />
                }
                onClick={handlePlayPause1}
              >
                {isPlaying1 ? "Pause" : "Play"}
              </Button>
              <Button
                className={styles.Download}
                icon={<DownloadOutlined />}
                onClick={downloadAudio1}
              >
                Download
              </Button>
            </div>
          )}

          <div
            className={styles.waveform}
            ref={waveformRef2}
            onClick={handlePlayPause2}
            style={{ cursor: "pointer" }}
          />
          {audioUrl2 && (
            <div className={styles.controls}>
              <Button
                className={styles.PlayButton}
                icon={
                  isPlaying2 ? <PauseCircleOutlined /> : <PlayCircleOutlined />
                }
                onClick={handlePlayPause2}
              >
                {isPlaying2 ? "Pause" : "Play"}
              </Button>
              <Button
                className={styles.Download}
                icon={<DownloadOutlined />}
                onClick={downloadAudio2}
              >
                Download
              </Button>
            </div>
          )}
        </div>
      ),
    },
    {
      label: <div className={styles.Tabs}>Combined</div>,
      key: "2",
      children: <VC_InferenceCombineTab audioUrl={audioUrlCombined} />,
    },
  ];

  return (
    <div className={styles.Button}>
      <Button
        className={styles.VCButton}
        type="primary"
        icon={<PoweroffOutlined />}
        loading={loadings[1]}
        onClick={() => enterLoading(1)}
      >
        Start Voice Conversion
      </Button>

      <Tabs className={styles.Tabs} items={tabsItems} />
    </div>
  );
};

export default VC_InferenceTab;
