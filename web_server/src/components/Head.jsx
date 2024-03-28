import { useState } from "react";
import styles from "./head.module.css";
import { Navbar, Container, Nav } from "react-bootstrap";
import { useNavigate } from "react-router-dom";

export default function Head() {
  let navigate = useNavigate();
  return (
    <div>
      <Navbar bg="grey" data-bs-theme="dark">
        <Container>
          <Navbar.Brand href="/">SweetAICoverSystem</Navbar.Brand>
          <Nav className="me-auto">
            <Nav.Link
              onClick={() => {
                navigate("/separation");
              }}
            >
              Separation
            </Nav.Link>
            <Nav.Link
              onClick={() => {
                navigate("/VCtrain");
              }}
            >
              Train
            </Nav.Link>
            <Nav.Link
              onClick={() => {
                navigate("/VCinference");
              }}
            >
              Voice Conversion
            </Nav.Link>
          </Nav>
        </Container>
      </Navbar>
    </div>
  );
}
