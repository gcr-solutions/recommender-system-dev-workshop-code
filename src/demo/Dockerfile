# first stage
FROM public.ecr.aws/t8u1z3c8/python:3.8 AS builder
COPY requirements.txt .

# install dependencies to the local user directory (eg. /root/.local)
RUN pip install --user -r requirements.txt
COPY ./ .

# second unnamed stage
FROM public.ecr.aws/t8u1z3c8/python:3.8-slim
WORKDIR /code

# copy only the dependencies installation from the 1st stage image
COPY --from=builder /root/.local/bin /root/.local
COPY --from=builder /root/.local/lib /root/.local
COPY ./ .


# update PATH environment variable
ENV PATH=/root/.local:$PATH
ENV PYTHONPATH=/root/.local:/root/.local/python3.8/site-packages

CMD [ "python", "./server.py" ]