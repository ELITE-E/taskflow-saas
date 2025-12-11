from django.contrib.auth.base_user import BaseUserManager

class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier 
    for authentication instead of usernames.

    """
    def create_user(self,email,password,**extra_fields):
        """
        Docstring for create_user
        Creates and saves a user with the given email and password.
        Performs strong validation on email address.
        """

        if not email:
            raise ValueError('The email must be set!')

        #normalize the email(make domain part lowercase ) for consistency
        email=self.normalize_email(email)

        #Instantiate the user model
        user=self.model(email=email,**extra_fields)

        #Set the passworg using django builtin hashing
        user.set_password(password)

        #Save to the primary db
        user.save(using=self._db)

        return user

    def create_superuser(self,email,password,**extra_fields):
        """
        Creates a superuser with the given email and password
        The superuser is both active/isStaff/isSuperuser at once 
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True) # Superusers must be active

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)
    