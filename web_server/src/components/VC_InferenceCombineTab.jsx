import React, { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import { Button } from "antd";
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  DownloadOutlined,
} from "@ant-design/icons";

const VC_InferenceCombineTab = ({ audioUrl }) => {
  const waveformRef = useRef(null);
  const wavesurfer = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);

  useEffect(() => {
    if (waveformRef.current) {
      wavesurfer.current = WaveSurfer.create({
        container: waveformRef.current,
        waveColor: "red",
        progressColor: "orange",
        cursorColor: "transparent",
        height: 200,
      });

      wavesurfer.current.on("play", () => setIsPlaying(true));
      wavesurfer.current.on("pause", () => setIsPlaying(false));
      wavesurfer.current.on("finish", () => setIsPlaying(false));

      if (audioUrl) {
        wavesurfer.current.load(audioUrl);
      }
    }

    return () => wavesurfer.current?.destroy();
  }, [audioUrl]);

  const handlePlayPause = () => {
    wavesurfer.current.playPause();
  };

  return (
    <div>
      <div
        ref={waveformRef}
        onClick={handlePlayPause}
        style={{ cursor: "pointer" }}
      />
      <div style={{ marginTop: 20 }}>
        {audioUrl && (
          <Button
            icon={isPlaying ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={handlePlayPause}
            style={{ marginRight: 10 }}
          >
            {isPlaying ? "Pause" : "Play"}
          </Button>
        )}
        {audioUrl && (
          <Button icon={<DownloadOutlined />} href={audioUrl} download>
            Download
          </Button>
        )}
      </div>
    </div>
  );
};

export default VC_InferenceCombineTab;
