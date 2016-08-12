""" Handles operation related to files. """
import os


def file_reader(file_path, file_name):
    """
    Reads from a file.
    :param file_path: str the path to the file.
    :param file_name: str the name of the file.
    :return: list of lines or None if no file exists.
    """
    file_content = []
    try:
        with open(file_path + file_name, mode='r') as f:
            for line in f:
                file_content.append(line.rstrip('\n'))
            return file_content
    except IOError:
        return None


def file_writer(file_path, file_name, write_this):
    """
    Write to file line by line.
    :param file_path: str the path to the file.
    :param file_name: str the name of the file.
    :param write_this: str the content to write.
    :return:
    """
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    with open(file_path + file_name, mode='a') as f:
        f.write(write_this + '\n')


def delete_file(file_path, file_name):
    """
    Deletes a file entirely.
    :param file_path: str the path to the file.
    :param file_name: str the file name.
    :return: True if deleted, else False
    """
    if os.path.isfile(file_path + file_name):
        os.remove(file_path + file_name)
        return True
    return False


def delete_file_content(file_path, file_name):
    """
    Deletes all content from a file.
    :param file_path: str the path to the file.
    :param file_name: str the name of the file.
    """
    open(file_path + file_name, mode='w').close()


def remove_from_file(file_path, file_name, remove):
    """
    Removes a line from a file.
    :param file_path: str the path to the file.
    :param file_name: str the name of the file.
    :param remove: str the line to remove.
    :return: True on success else False
    """
    file_list = file_reader(file_path, file_name)
    if file_list is not None:
        if remove in file_list:
            file_list.remove(remove)
            delete_file_content(file_path, file_name)
            for line in file_list:
                file_writer(file_path, file_name, line)
            return True
        return False
    return False
