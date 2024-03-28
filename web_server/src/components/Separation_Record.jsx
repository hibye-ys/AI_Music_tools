import React, { useState, useEffect } from "react";
import WaveSurfer from "wavesurfer.js";
import RecordRTC from "recordrtc";
import styles from "./separation_record.module.css";
import { Button } from "antd";
import { PlayCircleOutlined, PauseCircleOutlined } from "@ant-design/icons"; // 아이콘 import 추가
import { TbRecordMail, TbRecordMailOff } from "react-icons/tb";

const WaveformRecorder = () => {
  const [recorder, setRecorder] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [wavesurfer, setWavesurfer] = useState(null);
  const [latestRecording, setLatestRecording] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const toggleRecording = () => {
    if (isRecording) {
      recorder.stopRecording(() => {
        const blob = recorder.getBlob();
        const url = URL.createObjectURL(blob);
        setLatestRecording({ url, blob });
        if (wavesurfer) {
          wavesurfer.loadBlob(blob);
        }
      });
      setIsRecording(false);
    } else {
      navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
        const newRecorder = new RecordRTC(stream, {
          type: "audio",
          mimeType: "audio/wav",
          recorderType: RecordRTC.StereoAudioRecorder,
          numberOfAudioChannels: 1,
          sampleRate: 48000,
        });
        newRecorder.startRecording();
        setRecorder(newRecorder);
        setIsRecording(true);
      });
    }
  };

  useEffect(() => {
    const newWavesurfer = WaveSurfer.create({
      container: "#waveform",
      waveColor: "violet",
      progressColor: "purple",
    });

    setWavesurfer(newWavesurfer);

    return () => {
      newWavesurfer.destroy();
    };
  }, []);

  const playAudio = () => {
    if (wavesurfer) {
      wavesurfer.playPause();
      setIsPlaying(!isPlaying);
    }
  };

  return (
    <div>
      <div id="waveform"></div>
      <Button
        icon={isRecording ? <TbRecordMailOff /> : <TbRecordMail />}
        className={styles.recording}
        onClick={toggleRecording}
      >
        {isRecording ? "Stop Recording" : "Start Recording"}
      </Button>
      <Button
        icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
        className={styles.PlayPause}
        onClick={playAudio}
      >
        {isPlaying ? "Pause" : "Play"}
      </Button>
      {latestRecording && (
        <button className={styles.Download}>
          <a href={latestRecording.url} download="recording.wav">
            Download
          </a>
        </button>
      )}
    </div>
  );
};

export default WaveformRecorder;
