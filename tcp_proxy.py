import asyncio
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

REMOTE = os.environ.get("REMOTE_POOL", "minotaurx.na.mine.zpool.ca:7019")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "3333"))

remote_host, remote_port = REMOTE.split(":")
remote_port = int(remote_port)

async def handle_client(local_reader, local_writer):
    addr = local_writer.get_extra_info('peername')
    logging.info(f"Client connected: {addr} -> {remote_host}:{remote_port}")
    try:
        remote_reader, remote_writer = await asyncio.open_connection(remote_host, remote_port)
    except Exception as e:
        logging.error(f"Cannot connect to {remote_host}:{remote_port}: {e}")
        local_writer.close()
        return

    async def pipe(reader, writer, direction):
        try:
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception as e:
            logging.debug(f"{direction} closed: {e}")
        finally:
            writer.close()

    await asyncio.gather(
        pipe(local_reader, remote_writer, "client->remote"),
        pipe(remote_reader, local_writer, "remote->client")
    )
    logging.info(f"Client disconnected: {addr}")

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", LISTEN_PORT)
    logging.info(f"Listening on 0.0.0.0:{LISTEN_PORT}, forwarding to {remote_host}:{remote_port}")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Proxy stopped")
