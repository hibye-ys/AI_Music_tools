import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <ConfigProvider theme={{ cssVar: { key: "app" } }}>
        <App />
      </ConfigProvider>
    </BrowserRouter>
  </React.StrictMode>
);
