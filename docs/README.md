
# Pepper Web Server

## Description
This project provides a web server to remotely control and monitor a Pepper robot. Key features include:

- Live video streaming from Pepper's camera.
- Control of Pepper's movements (head, arms, etc.).
- Text-to-Speech (TTS) commands.
- Remote execution of Python code on the server.

## Project Structure

```
pepper_web_server/
├── src/
│   ├── pepper_server.py        # Main server to control the robot
│   ├── start_pepper_server.sh  # Script to start the server
├── templates/
│   └── index.html              # Main HTML template for the web interface
├── tests/
│   ├── audio_server.py         # Audio transmission test
│   ├── receiver_all_2.py       # Data reception test
│   └── script_video.py         # Video handling test
├── docs/
│   └── README.md               # Project documentation
├── requirements.txt            # Project dependencies
```

## Requirements

- Python 2.7 (compatible with NAOqi and Pepper's environment)
- Pepper robot configured on the same network
- Dependencies listed in `requirements.txt`

## Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/rafaelhernandezrios/pepper_web_server.git
   cd pepper_web_server
   ```

2. Install the necessary dependencies (ensure you are in a Python 2.7 environment):

   ```bash
   pip install -r requirements.txt
   ```

3. Transfer the files to the Pepper robot:

   ```bash
   scp -r . nao@<robot_ip>:/home/nao/pepper_web_server
   ```

4. Access the Pepper robot via SSH and start the server:

   ```bash
   ssh nao@<robot_ip>
   cd /home/nao/pepper_web_server/src
   bash start_pepper_server.sh
   ```

5. Open a browser and navigate to `http://<robot_ip>:5000` to interact with the robot.

## Usage

### Key Features

#### 1. Video Streaming
- Live video from Pepper's camera is displayed on the web interface.

#### 2. Movement Control
- Control movements of Pepper's head, arms, and other joints using sliders or buttons in the interface.

#### 3. Text-to-Speech (TTS)
- Enter text in the interface, and Pepper will speak it aloud.

#### 4. Python Code Execution
- Write and execute Python code from the web interface to send commands to the robot.

## Test Scripts
- **audio_server.py**: Manages and tests audio transmission.
- **receiver_all_2.py**: Tests data reception from Pepper.
- **script_video.py**: Handles and tests video streaming.

## Recommendations

### Using GUI-based Tools for File Transfers
For users unfamiliar with the command line, graphical tools such as [WinSCP](https://winscp.net) (Windows) or [Cyberduck](https://cyberduck.io) (macOS) are highly recommended for transferring files to Pepper via SSH. These tools provide a user-friendly interface to upload and manage files on the robot.

### Ensuring Compatibility
- **Python 2.7**: This project is designed to run in Pepper's environment, which uses Python 2.7 and the NAOqi framework. Make sure all dependencies are compatible.

- **Running in Pepper's Environment**: The `pepper_server.py` file must be executed directly on Pepper's operating system to ensure access to its APIs and hardware.

## Contributing

Contributions are welcome. If you want to collaborate:

1. Fork the repository.
2. Create a branch for your feature:
   ```bash
   git checkout -b new-feature
   ```
3. Submit a pull request describing your changes.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.
