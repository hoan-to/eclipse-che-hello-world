FROM quay.io/eclipse/che-python-3.8:7.33.1

USER 0

RUN apt update
RUN apt install libtiff5-dev libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev libfribidi-dev tcl8.6-dev tk8.6-dev python-tk -y
RUN pip3 install requests
RUN pip3 install hrv
RUN pip3 install py-ecg-detectors