FROM python:3.8 as py38
ENV PYTHONUNBUFFERED 1

WORKDIR /home/py

COPY ./ /home/py
RUN pip install .[dev]


FROM python:3.9 as py39
ENV PYTHONUNBUFFERED 1

WORKDIR /home/py

COPY ./ /home/py
RUN pip install .[dev]

FROM python:3.10 as py310
ENV PYTHONUNBUFFERED 1

WORKDIR /home/py

COPY ./ /home/py
RUN pip install .[dev]

FROM python:3.11 as py311
ENV PYTHONUNBUFFERED 1

WORKDIR /home/py

COPY ./ /home/py
RUN pip install .[dev]

FROM python:3.12 as py312
ENV PYTHONUNBUFFERED 1

WORKDIR /home/py

COPY ./ /home/py
RUN pip install .[dev]
